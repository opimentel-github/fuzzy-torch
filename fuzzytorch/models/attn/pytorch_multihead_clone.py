from __future__ import print_function
from __future__ import division

import torch
from torch._C import _is_torch_function_enabled, _disabled_torch_function_impl

from torch import Tensor
from torch.nn import Module, Parameter, Linear
from torch.nn.init import xavier_uniform_, constant_, eye_
from torch.nn import functional as F
from torch.nn.functional import linear, softmax, dropout
<<<<<<< HEAD
from torch.overrides import has_torch_function, handle_torch_function
=======
from typing import Dict, Set, List, Any, Callable, Iterable

def handle_torch_function(
		public_api: Callable, relevant_args: Iterable[Any], *args, **kwargs) -> Any:
	"""Implement a function with checks for ``__torch_function__`` overrides.

	See torch::autograd::handle_torch_function for the equivalent of this
	function in the C++ implementation.

	Arguments
	---------
	public_api : function
		Function exposed by the public torch API originally called like
		``public_api(*args, **kwargs)`` on which arguments are now being
		checked.
	relevant_args : iterable
		Iterable of arguments to check for __torch_function__ methods.
	args : tuple
		Arbitrary positional arguments originally passed into ``public_api``.
	kwargs : tuple
		Arbitrary keyword arguments originally passed into ``public_api``.

	Returns
	-------
	object
		Result from calling ``implementation`` or an ``__torch_function__``
		method, as appropriate.

	Raises
	------
	TypeError : if no implementation is found.

	Example
	-------
	>>> def func(a):
	...     if type(a) is not torch.Tensor:  # This will make func dispatchable by __torch_function__
	...         return handle_torch_function(func, (a,), a)
	...     return a + 0
	"""
	# Check for __torch_function__ methods.
	overloaded_args = _get_overloaded_args(relevant_args)
	# overloaded_args already have unique types.
	types = tuple(map(type, overloaded_args))

	# Call overrides
	for overloaded_arg in overloaded_args:
		# Use `public_api` instead of `implementation` so __torch_function__
		# implementations can do equality/identity comparisons.
		result = overloaded_arg.__torch_function__(public_api, types, args, kwargs)

		if result is not NotImplemented:
			return result

	func_name = '{}.{}'.format(public_api.__module__, public_api.__name__)
	raise TypeError("no implementation found for '{}' on types that implement "
					'__torch_function__: {}'
					.format(func_name, [type(arg) for arg in overloaded_args]))

def has_torch_function(relevant_args: Iterable[Any]) -> bool:
	"""Check for __torch_function__ implementations in the elements of an iterable.

	Considers exact ``Tensor`` s non-dispatchable.

	Arguments
	---------
	relevant_args : iterable
		Iterable or aguments to check for __torch_function__ methods.

	Returns
	-------
	bool
		True if any of the elements of relevant_args have __torch_function__
		implementations, False otherwise.

	See Also
	________
	torch.is_tensor_like
		Checks if something is a Tensor-like, including an exact ``Tensor``.
	"""
	return _is_torch_function_enabled() and any(
		type(a) is not torch.Tensor and
		getattr(a, '__torch_function__', _disabled_torch_function_impl)
		is not _disabled_torch_function_impl
		for a in relevant_args
	)
>>>>>>> fd60ce4fbd947f49e545e61ddbd3bb485257b5d2

class MultiheadAttention(Module):
	__annotations__ = {
		'bias_k': torch._jit_internal.Optional[torch.Tensor],
		'bias_v': torch._jit_internal.Optional[torch.Tensor],
	}
	__constants__ = ['q_proj_weight', 'k_proj_weight', 'v_proj_weight', 'in_proj_weight']

	def __init__(self, embed_dim, num_heads, dropout=0., bias=True, add_bias_kv=False, add_zero_attn=False, kdim=None, vdim=None):
		#super(MultiheadAttention, self).__init__()
		super().__init__()
		self.embed_dim = embed_dim
		self.kdim = kdim if kdim is not None else embed_dim
		self.vdim = vdim if vdim is not None else embed_dim
		self._qkv_same_embed_dim = self.kdim == embed_dim and self.vdim == embed_dim

		self.num_heads = num_heads
		self.dropout = dropout
		self.head_dim = embed_dim // num_heads
		assert self.head_dim * num_heads == self.embed_dim, "embed_dim must be divisible by num_heads"

		if self._qkv_same_embed_dim is False:
			self.q_proj_weight = Parameter(torch.Tensor(embed_dim, embed_dim))
			self.k_proj_weight = Parameter(torch.Tensor(embed_dim, self.kdim))
			self.v_proj_weight = Parameter(torch.Tensor(embed_dim, self.vdim))
			#print('q_proj_weight',self.q_proj_weight.shape)
			#print('k_proj_weight',self.k_proj_weight.shape)
			#print('v_proj_weight',self.v_proj_weight.shape)
			self.register_parameter('in_proj_weight', None)
		else:
			self.in_proj_weight = Parameter(torch.empty(3 * embed_dim, embed_dim))
			self.register_parameter('q_proj_weight', None)
			self.register_parameter('k_proj_weight', None)
			self.register_parameter('v_proj_weight', None)

		if bias:
			self.in_proj_bias = Parameter(torch.empty(3 * embed_dim))
		else:
			self.register_parameter('in_proj_bias', None)
		self.out_proj = Linear(embed_dim, embed_dim, bias=bias)

		if add_bias_kv:
			self.bias_k = Parameter(torch.empty(1, 1, embed_dim))
			self.bias_v = Parameter(torch.empty(1, 1, embed_dim))
		else:
			self.bias_k = self.bias_v = None

		self.add_zero_attn = add_zero_attn

		self._reset_parameters()

	def _reset_parameters(self):
		if self._qkv_same_embed_dim:
			xavier_uniform_(self.in_proj_weight)
		else:
			xavier_uniform_(self.q_proj_weight)
			xavier_uniform_(self.k_proj_weight)
			xavier_uniform_(self.v_proj_weight)

		if self.in_proj_bias is not None:
			constant_(self.in_proj_bias, 0.)
			constant_(self.out_proj.bias, 0.)
		if self.bias_k is not None:
			xavier_normal_(self.bias_k)
		if self.bias_v is not None:
			xavier_normal_(self.bias_v)

	def __setstate__(self, state):
		super(MultiheadAttention, self).__setstate__(state)

		# Support loading old MultiheadAttention checkpoints generated by v1.1.0
		if 'self._qkv_same_embed_dim' not in self.__dict__:
			self._qkv_same_embed_dim = True

	def forward(self, query, key, value, key_padding_mask=None,
				need_weights=True, attn_mask=None):

		#print(self.uses_query_eye);print(self.q_proj_weight)
		#print('_qkv_same_embed_dim',self._qkv_same_embed_dim)
		if not self._qkv_same_embed_dim:
			return multi_head_attention_forward(
				query, key, value, self.embed_dim, self.num_heads,
				self.in_proj_weight, self.in_proj_bias,
				self.bias_k, self.bias_v, self.add_zero_attn,
				self.dropout, self.out_proj.weight, self.out_proj.bias,
				training=self.training,
				key_padding_mask=key_padding_mask, need_weights=need_weights,
				attn_mask=attn_mask, use_separate_proj_weight=True,
				q_proj_weight=self.q_proj_weight, k_proj_weight=self.k_proj_weight,
				v_proj_weight=self.v_proj_weight)
		else:
			return multi_head_attention_forward(
				query, key, value, self.embed_dim, self.num_heads,
				self.in_proj_weight, self.in_proj_bias,
				self.bias_k, self.bias_v, self.add_zero_attn,
				self.dropout, self.out_proj.weight, self.out_proj.bias,
				training=self.training,
				key_padding_mask=key_padding_mask, need_weights=need_weights,
				attn_mask=attn_mask)


def multi_head_attention_forward(query,                           # type: Tensor
								 key,                             # type: Tensor
								 value,                           # type: Tensor
								 embed_dim_to_check,              # type: int
								 num_heads,                       # type: int
								 in_proj_weight,                  # type: Tensor
								 in_proj_bias,                    # type: Tensor
								 bias_k,                          # type: Optional[Tensor]
								 bias_v,                          # type: Optional[Tensor]
								 add_zero_attn,                   # type: bool
								 dropout_p,                       # type: float
								 out_proj_weight,                 # type: Tensor
								 out_proj_bias,                   # type: Tensor
								 training=True,                   # type: bool
								 key_padding_mask=None,           # type: Optional[Tensor]
								 need_weights=True,               # type: bool
								 attn_mask=None,                  # type: Optional[Tensor]
								 use_separate_proj_weight=False,  # type: bool
								 q_proj_weight=None,              # type: Optional[Tensor]
								 k_proj_weight=None,              # type: Optional[Tensor]
								 v_proj_weight=None,              # type: Optional[Tensor]
								 static_k=None,                   # type: Optional[Tensor]
								 static_v=None                    # type: Optional[Tensor]
								 ):

	if not torch.jit.is_scripting():
		tens_ops = (query, key, value, in_proj_weight, in_proj_bias, bias_k, bias_v,
					out_proj_weight, out_proj_bias)
		if any([type(t) is not Tensor for t in tens_ops]) and has_torch_function(tens_ops):
			return handle_torch_function(
				multi_head_attention_forward, tens_ops, query, key, value,
				embed_dim_to_check, num_heads, in_proj_weight, in_proj_bias,
				bias_k, bias_v, add_zero_attn, dropout_p, out_proj_weight,
				out_proj_bias, training=training, key_padding_mask=key_padding_mask,
				need_weights=need_weights, attn_mask=attn_mask,
				use_separate_proj_weight=use_separate_proj_weight,
				q_proj_weight=q_proj_weight, k_proj_weight=k_proj_weight,
				v_proj_weight=v_proj_weight, static_k=static_k, static_v=static_v)
	tgt_len, bsz, embed_dim = query.size()
	assert embed_dim == embed_dim_to_check
	assert key.size() == value.size() # WEIRD

	head_dim = embed_dim // num_heads
	assert head_dim * num_heads == embed_dim, "embed_dim must be divisible by num_heads"
	scaling = float(head_dim) ** -0.5

	if not use_separate_proj_weight:
		if torch.equal(query, key) and torch.equal(key, value):
			# self-attention
			q, k, v = linear(query, in_proj_weight, in_proj_bias).chunk(3, dim=-1)

		elif torch.equal(key, value):
			# encoder-decoder attention
			# This is inline in_proj function with in_proj_weight and in_proj_bias
			_b = in_proj_bias
			_start = 0
			_end = embed_dim
			_w = in_proj_weight[_start:_end, :]
			if _b is not None:
				_b = _b[_start:_end]
			q = linear(query, _w, _b)

			if key is None:
				assert value is None
				k = None
				v = None
			else:

				# This is inline in_proj function with in_proj_weight and in_proj_bias
				_b = in_proj_bias
				_start = embed_dim
				_end = None
				_w = in_proj_weight[_start:, :]
				if _b is not None:
					_b = _b[_start:]
				k, v = linear(key, _w, _b).chunk(2, dim=-1)

		else:
			# This is inline in_proj function with in_proj_weight and in_proj_bias
			_b = in_proj_bias
			_start = 0
			_end = embed_dim
			_w = in_proj_weight[_start:_end, :]
			if _b is not None:
				_b = _b[_start:_end]
			q = linear(query, _w, _b)

			# This is inline in_proj function with in_proj_weight and in_proj_bias
			_b = in_proj_bias
			_start = embed_dim
			_end = embed_dim * 2
			_w = in_proj_weight[_start:_end, :]
			if _b is not None:
				_b = _b[_start:_end]
			k = linear(key, _w, _b)

			# This is inline in_proj function with in_proj_weight and in_proj_bias
			_b = in_proj_bias
			_start = embed_dim * 2
			_end = None
			_w = in_proj_weight[_start:, :]
			if _b is not None:
				_b = _b[_start:]
			v = linear(value, _w, _b)
	else:
		q_proj_weight_non_opt = torch.jit._unwrap_optional(q_proj_weight)
		len1, len2 = q_proj_weight_non_opt.size()
		assert len1 == embed_dim and len2 == query.size(-1)

		k_proj_weight_non_opt = torch.jit._unwrap_optional(k_proj_weight)
		len1, len2 = k_proj_weight_non_opt.size()
		assert len1 == embed_dim and len2 == key.size(-1)

		v_proj_weight_non_opt = torch.jit._unwrap_optional(v_proj_weight)
		len1, len2 = v_proj_weight_non_opt.size()
		assert len1 == embed_dim and len2 == value.size(-1)

		if in_proj_bias is not None:
			q = linear(query, q_proj_weight_non_opt, in_proj_bias[0:embed_dim])
			k = linear(key, k_proj_weight_non_opt, in_proj_bias[embed_dim:(embed_dim * 2)])
			v = linear(value, v_proj_weight_non_opt, in_proj_bias[(embed_dim * 2):])
		else:
			q = linear(query, q_proj_weight_non_opt, in_proj_bias)
			k = linear(key, k_proj_weight_non_opt, in_proj_bias)
			v = linear(value, v_proj_weight_non_opt, in_proj_bias)
	q = q * scaling

	if attn_mask is not None:
		if attn_mask.dim() == 2:
			attn_mask = attn_mask.unsqueeze(0)
			if list(attn_mask.size()) != [1, query.size(0), key.size(0)]:
				raise RuntimeError('The size of the 2D attn_mask is not correct.')
		elif attn_mask.dim() == 3:
			if list(attn_mask.size()) != [bsz * num_heads, query.size(0), key.size(0)]:
				raise RuntimeError('The size of the 3D attn_mask is not correct.')
		else:
			raise RuntimeError("attn_mask's dimension {} is not supported".format(attn_mask.dim()))
		# attn_mask's dim is 3 now.

	if bias_k is not None and bias_v is not None:
		if static_k is None and static_v is None:
			k = torch.cat([k, bias_k.repeat(1, bsz, 1)])
			v = torch.cat([v, bias_v.repeat(1, bsz, 1)])
			if attn_mask is not None:
				attn_mask = pad(attn_mask, (0, 1))
			if key_padding_mask is not None:
				key_padding_mask = pad(key_padding_mask, (0, 1))
		else:
			assert static_k is None, "bias cannot be added to static key."
			assert static_v is None, "bias cannot be added to static value."
	else:
		assert bias_k is None
		assert bias_v is None

	#print('q',q.shape) # txbxhidden
	initial_q = q
	'''
	q[:,0,:] = 0
	q[:,1,:] = 1
	q[:,2,:] = 2
	q[:,3,:] = 3
	'''
	q = q.contiguous().view(tgt_len, bsz * num_heads, head_dim)
	#q_out = initial_q.contiguous().view(tgt_len, bsz, num_heads, head_dim).transpose(0,1).transpose(2,1)
	#k_out = k.contiguous().view(tgt_len, bsz, num_heads, head_dim).transpose(0,1).transpose(2,1)
	#print('q_out',q_out.shape,'k_out',k_out.shape)
	#q_out = torch.cat([q_out, k_out], dim=-1)
	#print('TIME ---------',q_out[0,0,:,0])
	'''
	print('q',q.shape,q[0,(0)*bsz:(0+1)*bsz,0])
	for bb in range(bsz):
		print('----->'+str(bb))
		print('q_out',q_out.shape,q_out[0,bb,:,0])
	print('=======')
	'''

	q = q.transpose(0, 1)

	if k is not None:
		k = k.contiguous().view(-1, bsz * num_heads, head_dim).transpose(0, 1)
	if v is not None:
		v = v.contiguous().view(-1, bsz * num_heads, head_dim).transpose(0, 1)

	if static_k is not None:
		assert static_k.size(0) == bsz * num_heads
		assert static_k.size(2) == head_dim
		k = static_k

	if static_v is not None:
		assert static_v.size(0) == bsz * num_heads
		assert static_v.size(2) == head_dim
		v = static_v

	src_len = k.size(1)

	if key_padding_mask is not None:
		assert key_padding_mask.size(0) == bsz
		assert key_padding_mask.size(1) == src_len

	if add_zero_attn:
		src_len += 1
		k = torch.cat([k, torch.zeros((k.size(0), 1) + k.size()[2:], dtype=k.dtype, device=k.device)], dim=1)
		v = torch.cat([v, torch.zeros((v.size(0), 1) + v.size()[2:], dtype=v.dtype, device=v.device)], dim=1)
		if attn_mask is not None:
			attn_mask = pad(attn_mask, (0, 1))
		if key_padding_mask is not None:
			key_padding_mask = pad(key_padding_mask, (0, 1))

	attn_output_weights = torch.bmm(q, k.transpose(1, 2)) # BMM
	#print(attn_output_weights.shape)
	#q_out = q.view(tgt_len, num_heads, bsz, head_dim)
	assert list(attn_output_weights.size()) == [bsz * num_heads, tgt_len, src_len]

	if attn_mask is not None:
		attn_output_weights += attn_mask

	if key_padding_mask is not None:
		attn_output_weights = attn_output_weights.view(bsz, num_heads, tgt_len, src_len)
		attn_output_weights = attn_output_weights.masked_fill(
			key_padding_mask.unsqueeze(1).unsqueeze(2),
			float('-inf'),
		)
		attn_output_weights = attn_output_weights.view(bsz * num_heads, tgt_len, src_len)

	attn_output_weights = softmax(attn_output_weights, dim=-1) # (bh,t,q)
	attn_output_weights = dropout(attn_output_weights, p=dropout_p, training=training)

	attn_output = torch.bmm(attn_output_weights, v)
	assert list(attn_output.size()) == [bsz * num_heads, tgt_len, head_dim]
	attn_output = attn_output.transpose(0, 1).contiguous().view(tgt_len, bsz, embed_dim)
	attn_output = linear(attn_output, out_proj_weight, out_proj_bias)

	if need_weights:
		# average attention weights over heads
		attn_output_weights = attn_output_weights.view(bsz, num_heads, tgt_len, src_len) # bxhxtxq
		#attn_output_weights = attn_output_weights.sum(dim=1) / num_heads # bxtxq # is a mean!
		#print('attn_output_weights',attn_output_weights.shape)
		return attn_output, attn_output_weights
	else:
		return attn_output