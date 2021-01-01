from __future__ import print_function
from __future__ import division
from . import C_

import torch
import torch.nn as nn
import torch.nn.functional as F
from .. import non_linear
from .. import utils
from . import utils as attn_utils
from ..basics import MLP
from torch.nn.init import xavier_uniform_, constant_, eye_
from flamingchoripan import strings as strings
from flamingchoripan import lists as lists
from .pytorch_multihead_clone import MultiheadAttention

###################################################################################################################################################

class SelfAttn(nn.Module):
	def __init__(self, input_dims:int, output_dims:int, max_curve_length,
		num_heads=2,
		activation='linear',
		in_dropout=0.0,
		out_dropout=0.0,
		attn_dropout=0.0,
		mlp_dropout=0.0,
		bias=True,
		uses_seq_len_wise_batchnorm=True,
		**kwargs):
		super().__init__()

		### CHECKS
		assert in_dropout>=0 and in_dropout<=1
		assert out_dropout>=0 and out_dropout<=1
		assert attn_dropout>=0 and attn_dropout<=1
		assert mlp_dropout>=0 and mlp_dropout<=1

		self.input_dims = input_dims
		self.output_dims = output_dims
		self.max_curve_length = max_curve_length
		self.num_heads = num_heads
		self.activation = activation
		self.in_dropout = in_dropout
		self.out_dropout = out_dropout
		self.attn_dropout = attn_dropout
		self.mlp_dropout = mlp_dropout
		self.bias = bias
		self.uses_seq_len_wise_batchnorm = uses_seq_len_wise_batchnorm

		### ATTN
		attn_kwargs = {
			'dropout':self.attn_dropout,
			'bias':self.bias,
			'add_bias_kv':False,
			'add_zero_attn':False,
			'kdim':None,
			'vdim':None,
		}
		self.mh_attn = MultiheadAttention(self.input_dims, self.num_heads, **attn_kwargs)
		self.in_dropout_f = nn.Dropout(self.in_dropout)
		self.out_dropout_f = nn.Dropout(self.out_dropout)
		self.register_buffer('src_mask', attn_utils.generate_square_subsequent_mask(self.max_curve_length))

		### MLP
		mlp_kwargs = {
			'activation':'relu', # transformer
			'in_dropout':0.,
			'out_dropout':0.,
			'bias':self.bias,
			'dropout':self.mlp_dropout,
			'last_activation':'linear', # transformer
		}
		self.mlp = MLP(self.input_dims, self.output_dims, [self.input_dims]*1, **mlp_kwargs)
		
		self.activation_f = non_linear.get_activation(self.activation)
		self.reset()

	def reset(self):
		pass

	def get_output_dims(self):
		return self.output_dims

	def __len__(self):
		return utils.count_parameters(self)
		
	def extra_repr(self):
		txt = strings.get_string_from_dict({
		'input_dims':self.input_dims,
		'output_dims':self.output_dims,
		'max_curve_length':self.max_curve_length,
		'num_heads':self.num_heads,
		'activation':self.activation,
		'in_dropout':self.in_dropout,
		'out_dropout':self.out_dropout,
		'attn_dropout':self.attn_dropout,
		'mlp_dropout':self.mlp_dropout,
		'bias':self.bias,
		}, ', ', '=')
		return txt

	def __repr__(self):
		txt = f'SelfAttn({self.extra_repr()})'
		txt += f'({len(self):,}[p])'
		return txt

	def forward(self, x, onehot, **kwargs):
		'''
		Parameters
		----------
		x (b,t,f): input tensor.
		onehot (b,t)

		Return
		----------
		x_out: (b,t,h): output tensor.
		scores: (b,h,t,qt)
		'''
		attn_kwargs = {
			'key_padding_mask':~onehot,
			'attn_mask':self.src_mask,
			'need_weights':True,
		}
		queries = self.in_dropout_f(x.permute(1,0,2))
		keys = self.in_dropout_f(x.permute(1,0,2))
		values = self.in_dropout_f(x.permute(1,0,2))
		contexts, scores = self.mh_attn(queries, keys, values, **attn_kwargs)
		x = contexts+values # res
		x = x.permute(1,0,2)
		assert torch.all(scores.sum(dim=-1)>=0.99999)

		x = self.mlp(x)+x # res
		x = self.activation_f(x, dim=-1)
		x = self.out_dropout_f(x)
		return x, scores

class MLSelfAttn(nn.Module):
	def __init__(self, input_dims:int, output_dims:int, embd_dims_list:list, max_curve_length,
		num_heads=2,
		activation='linear',
		last_activation='linear',
		in_dropout=0.0,
		dropout=0.0,
		out_dropout=0.0,
		attn_dropout=0.0,
		bias=True,
		uses_seq_len_wise_batchnorm=True,
		**kwargs):
		super().__init__()

		### CHECKS
		assert in_dropout>=0 and in_dropout<=1
		assert dropout>=0 and dropout<=1
		assert out_dropout>=0 and out_dropout<=1
		assert attn_dropout>=0 and attn_dropout<=1

		self.input_dims = input_dims
		self.output_dims = output_dims
		self.embd_dims_list = [self.input_dims]+embd_dims_list+[self.output_dims]
		self.max_curve_length = max_curve_length
		self.num_heads = num_heads
		self.activation = activation
		self.last_activation = last_activation
		self.in_dropout = in_dropout
		self.dropout = dropout
		self.out_dropout = out_dropout
		self.attn_dropout = attn_dropout
		self.bias = bias
		self.uses_seq_len_wise_batchnorm = uses_seq_len_wise_batchnorm

		activations = [activation]*(len(self.embd_dims_list)-1) # create activations along
		if not self.last_activation is None:
			activations[-1] = self.last_activation

		### MODULES
		self.self_attns = nn.ModuleList()
		for k in range(len(self.embd_dims_list)-1):
			input_dims_ = self.embd_dims_list[k]
			output_dims_ = self.embd_dims_list[k+1]
			attn_kwargs = {
				'num_heads':self.num_heads,
				'activation':activations[k],
				'in_dropout':self.in_dropout if k==0 else self.dropout,
				'out_dropout':self.out_dropout if k==len(self.embd_dims_list)-2 else 0.0,
				'attn_dropout':self.attn_dropout,
				'bias':self.bias,
				'uses_seq_len_wise_batchnorm':self.uses_seq_len_wise_batchnorm,
			}
			self_attn = SelfAttn(input_dims_, output_dims_, self.max_curve_length, **attn_kwargs)
			self.self_attns.append(self_attn)

		self.reset()

	def reset(self):
		for self_attn in self.self_attns:
			self_attn.reset()

	def __len__(self):
		return utils.count_parameters(self)

	def __repr__(self):
		resume = ''
		for k,self_attn in enumerate(self.self_attns):
			resume += f'  ({k}) - {str(self_attn)}\n'
		txt = f'MLSelfAttn(\n{resume})({len(self):,}[p])'
		return txt

	def forward(self, x, onehot, **kwargs):
		'''
		Parameters
		----------
		x (b,t,f): input tensor.
		onehot (b,t)

		Return
		----------
		x_out: (b,t,h): output tensor.
		layer_scores: list[(b,h,t,qt)]
		'''
		assert onehot.dtype==torch.bool
		assert len(onehot.shape)==2
		assert x.shape[:-1]==onehot.shape
		assert len(x.shape)==3

		layer_scores = []
		for k,self_attn in enumerate(self.self_attns):
			x, scores = self_attn(x, onehot, **kwargs)
			layer_scores.append(scores)
		return x, layer_scores

	def __len__(self):
		return utils.count_parameters(self)

	def __repr__(self):
		resume = ''
		for k,self_attn in enumerate(self.self_attns):
			resume += f'  ({k}) - {str(self_attn)}\n'
		txt = f'MLSelfAttn(\n{resume})({len(self):,}[p])'
		return txt