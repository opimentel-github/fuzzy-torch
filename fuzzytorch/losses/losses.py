from __future__ import print_function
from __future__ import division
from . import C_

import torch
import torch.nn.functional as F
import numpy as np
from . import losses

###################################################################################################################################################

class NewLossCrit:
	def __init__(self, fun, kwargs:dict={}):
		self.fun = fun
		self.kwargs = kwargs
		self.sublosses_names = None

def get_loss_text(loss, round_decimals:int=C_.LOSS_DECIMALS):
	f = '{:.'+str(round_decimals)+'f}'
	return f.format(loss)

def get_loss_from_losses(loss_crit, pred, target, round_decimals:int=C_.LOSS_DECIMALS):
	assert isinstance(loss_crit, losses.NewLossCrit)
	
	f_ret = loss_crit.fun(pred, target, **loss_crit.kwargs)
	assert isinstance(f_ret, list) or isinstance(f_ret, tuple)
	assert len(f_ret)==2

	finalloss, sublosses_dic = f_ret
	assert len(finalloss.shape)==0 # just 1 value tensor

	final_loss_test = get_loss_text(finalloss, round_decimals)
	sublosses_text = []
	for key in sublosses_dic.keys():
		assert len(sublosses_dic[key].shape)==0 # just 1 value tensor
		sublosses_text.append(get_loss_text(sublosses_dic[key], round_decimals))

	final_loss_test = f'{final_loss_test}'
	if len(sublosses_text)>0:
		final_loss_test +=f'={"+".join(sublosses_text)}'

	return finalloss, final_loss_test, sublosses_dic

############# LOSSES ZOO

def normal_kl(mu1, logvar1, mu2, logvar2):
	v1 = torch.exp(logvar1)
	v2 = torch.exp(logvar2)
	logstd1 = logvar1 / 2.0
	logstd2 = logvar2 / 2.0
	kl = logstd2 - logstd1 + ((v1 + (mu1 - mu2) ** 2.0) / (2.0 * v2)) - 0.5
	return kl

def log_normal_pdf(x, mean, logvar):
	const = torch.from_numpy(np.array([2. * np.pi])).float().to(x.device)
	const = torch.log(const)
	var = torch.exp(logvar)
	return -(const + logvar + (x - mean)**2 / var) / 2

def batch_crossentropy_manual(y_pred, y_target,
	class_weight=None,
	):
	assert y_pred.size()==y_target.size()
	batch_loss = -torch.sum(y_target.float() * torch.log(y_pred+EPS), dim=-1) # (b,...,c) > (b,...)
	return batch_loss # (b,...)

def batch_crossentropy(y_pred, y_target,
	model_output_is_with_softmax:bool=False,
	target_is_onehot:bool=True,
	class_weight=None,
	):
	# F.cross_entropy already uses softmax as preprocessing internally
	# F.cross_entropy uses target as labels, not onehot
	classes = y_pred.size()[-1]
	no_classes_shape = y_pred.size()[:-1]
	if target_is_onehot: # [[01],[10],[01],[01],[10]]
		if model_output_is_with_softmax:
			batch_loss = batch_crossentropy_manual(y_pred, y_target) # (b,...,c) > (b,...) # ugly case
		else:
			assert y_pred.shape==y_target.shape
			y_pred = y_pred.view(-1, classes)
			y_target = y_target.view(-1, classes).argmax(dim=-1)
			batch_loss = F.cross_entropy(y_pred, y_target, reduction='none') # (b,...,c) > (b)
			batch_loss = batch_loss.view(*no_classes_shape)

	else: # [0,1,3,4,2,0,1,1]
		if model_output_is_with_softmax:
			raise Exception('not implemented')
		else:
			assert y_pred.shape[0]==y_target.shape[0]
			assert len(y_pred.shape)==2
			assert len(y_target.shape)==1
			batch_loss = F.cross_entropy(y_pred.view(-1, classes), y_target.view(-1), reduction='none', weight=class_weight) # (b,...,c) > (b)
			batch_loss = batch_loss.view(*no_classes_shape)

	return batch_loss # (b,...)

def crossentropy(y_pred, y_target,
	model_output_is_with_softmax:bool=False,
	target_is_onehot:bool=True,
	pred_dict_key:str=None,
	target_dict_key:str=None,
	**kwargs):
	y_pred = (y_pred[pred_dict_key] if not pred_dict_key is None else y_pred)
	y_target = (y_target[target_dict_key] if not target_dict_key is None else y_target)
	
	batch_loss = batch_crossentropy(y_pred, y_target, model_output_is_with_softmax, target_is_onehot) # (b,c) > (b)
	batch_loss = batch_loss.mean(-1) # (b) > ()
	sublosses = {
		'loss/2':batch_loss/2,
		'loss/3':batch_loss/3,
	}
	return batch_loss, sublosses