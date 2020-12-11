import sys
import numpy as np
from flamingchoripan import C_ as C_fc

###################################################################################################################################################

EPS = 1e-10
DEFAULT_PADDING_MODE = 'same'
DEFAULT_ACTIVATION = 'relu'
DEFAULT_LAST_ACTIVATION = 'linear'

DEFAULT_CNN_KWARGS = {
	'kernel_size':3,
	'stride':1,
	'dilation':1,
}
DEFAULT_POOL_KWARGS = {
	'kernel_size':2,
	'stride':2,
	'dilation':1,
}

K_COUNTER_DURATION = 0
VAL_EPOCH_COUNTER_DURATION = 0
EARLYSTOP_EPOCH_DURATION = 21

SM_NO_SAVE = 'no_save'
SM_ALL = 'all'
SM_ONLY_ALL = 'only_all'
SM_ONLY_INF_LOSS = 'only_inf_loss'
SM_ONLY_INF_METRIC = 'only_inf_metric'
SM_ONLY_SUP_METRIC = 'only_sup_metric'

SAVE_FEXT = 'tfes'
KEY_KEY_SEP_CHAR = C_fc.KEY_KEY_SEP_CHAR
KEY_VALUE_SEP_CHAR = C_fc.KEY_VALUE_SEP_CHAR

DUMMY_TEXT = 'Dummy'

PLOT_FIGSIZE = (11,3)
PLOT_GRID_ALPHA = 0.25
PLOT_DPI = 80
#C_MAIN_LOSS = '#343434'
