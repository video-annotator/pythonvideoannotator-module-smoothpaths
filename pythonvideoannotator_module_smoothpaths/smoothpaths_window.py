import pyforms
from pysettings import conf
from pyforms import BaseWidget
from pyforms.Controls import ControlSlider
from pyforms.Controls import ControlButton
from pyforms.Controls import ControlEmptyWidget
from pyforms.Controls import ControlProgress

from pythonvideoannotator_models_gui.dialogs import DatasetsDialog
from pythonvideoannotator_models_gui.models.video.objects.object2d.datasets.path import Path
from pythonvideoannotator_models_gui.models.video.objects.object2d.datasets.value import Value

import numpy as np
from math import factorial
from pysettings import conf


def savitzky_golay(y, window_size, order=0, deriv=0, rate=1):
	try:
		window_size = np.abs(np.int(window_size))
		order = np.abs(np.int(order))
	except ValueError as msg:
		raise ValueError("window_size and order have to be of type int")
	if window_size % 2 != 1 or window_size < 1:
		raise TypeError("window_size size must be a positive odd number")
	if window_size < order + 2:
		raise TypeError("window_size is too small for the polynomials order")
	order_range = range(order+1)
	half_window = (window_size -1) // 2
	# precompute coefficients
	b = np.mat([[k**i for i in order_range] for k in range(-half_window, half_window+1)])
	m = np.linalg.pinv(b).A[deriv] * rate**deriv * factorial(deriv)
	# pad the signal at the extremes with
	# values taken from the signal itself
	firstvals = y[0] - np.abs( y[1:half_window+1][::-1] - y[0] )
	lastvals = y[-1] + np.abs(y[-half_window-1:-1][::-1] - y[-1])
	y = np.concatenate((firstvals, y, lastvals))
	return np.convolve( m[::-1], y, mode='valid')



class SmoothPathsWindow(BaseWidget):

	def __init__(self, parent=None):
		super(SmoothPathsWindow, self).__init__('Smooth paths', parent_win=parent)
		self.mainwindow = parent

		if conf.PYFORMS_USE_QT5:
			self.layout().setContentsMargins(5,5,5,5)
		else:
			self.layout().setMargin(5)
		self.setMinimumHeight(400)
		self.setMinimumWidth(800)



		self._datasets_panel= ControlEmptyWidget('Paths')
		self._progress  	= ControlProgress('Progress')		
		self._apply 		= ControlButton('Apply', checkable=True)

		self._winsize   = ControlSlider('Window size', 2, 2, 100)
		self._order  	= ControlSlider('Order', 0, 0, 10)
		self._deriv   	= ControlSlider('Derivate', 0, 0, 10)
		self._rate   	= ControlSlider('Rate', 0, 0, 10)

			
		self._formset = [
			'_datasets_panel',
			'=',
			'_winsize',
			'_order',
			'_deriv',
			'_rate', 
			' ',
			'_apply',
			'_progress'
		]

		self.load_order = ['_datasets_panel']

		self.datasets_dialog 		= DatasetsDialog(self)
		self._datasets_panel.value = self.datasets_dialog
		self.datasets_dialog.datasets_filter = lambda x: isinstance(x, (Path, Value))

		self._apply.value		= self.__apply_event
		self._apply.icon 		= conf.ANNOTATOR_ICON_PATH

		self._progress.hide()

	def init_form(self):
		super(SmoothPathsWindow, self). init_form()
		self.datasets_dialog.project = self.mainwindow.project

	###########################################################################
	### EVENTS ################################################################
	###########################################################################



	###########################################################################
	### PROPERTIES ############################################################
	###########################################################################

	@property
	def datasets(self): return self.datasets_dialog.datasets
	

	def __apply_event(self):

		if self._apply.checked:
			
			self._datasets_panel.enabled 	= False			
			self._apply.label 			= 'Cancel'

			total_2_analyse  = 0
			for video, (begin, end), datasets in self.datasets_dialog.selected_data:
				total_2_analyse += (end-begin+1)*2

			self._progress.min = 0
			self._progress.max = total_2_analyse
			self._progress.show()

			count = 0
			for video, (begin, end), datasets in self.datasets_dialog.selected_data:
				begin 	= int(begin)
				end 	= int(end)+1

				for dataset in datasets:
					if isinstance(dataset, Path):
						values = [dataset.get_position(index) for index in range(begin, end)]
					elif isinstance(dataset, Value):
						values = [dataset.get_value(index) for index in range(begin, end)]

					#remove the None positions
					for curr_idx in range(len(values)):
						if values[curr_idx] is None:

							#Search for a not None position on the past
							new_vals = None
							for prev_idx in range(curr_idx, 0, -1):
								new_vals = values[prev_idx]
								if new_vals is not None: break

							#Search for a not None position on the future
							if new_vals is None:
								for nex_idx in range(curr_idx, end):
									new_vals = values[nex_idx]
									if new_vals is not None: break

							#No positions were found, assume 0,0 position
							if new_vals is None:
								if isinstance(dataset, Path):
									new_vals = (0,0)
								elif isinstance(dataset, Value):
									new_vals = 0

							values[curr_idx]=new_vals
						
						self._progress.value = count
						count += 1

					winsize = self._winsize.value
					winsize = winsize+1 if (winsize % 2)==0 else winsize

					if isinstance(dataset, Path):
						xs = np.array([x for x, y in values])
						ys = np.array([y for x, y in values])
						xs = savitzky_golay(xs, winsize, self._order.value, self._deriv.value, self._rate.value)
						ys = savitzky_golay(ys, winsize, self._order.value, self._deriv.value, self._rate.value)
						for index in range(begin, end):
							pos = dataset.get_position(index)
							if pos is not None:
								dataset.set_position(index, xs[index], ys[index])						
							self._progress.value = count
							count += 1
					elif isinstance(dataset, Value):
						xs = np.array(values)
						xs = savitzky_golay(xs, winsize, self._order.value, self._deriv.value, self._rate.value)
						for index in range(begin, end):
							val = dataset.get_value(index)
							if val is not None:
								dataset.set_value(index, xs[index])						
							self._progress.value = count
							count += 1
					
					
					

				

			self._datasets_panel.enabled 	= True	
			self._apply.label 			= 'Apply'
			self._apply.checked 		= False
			self._progress.hide()





	


if __name__ == '__main__': 
	pyforms.startApp(SmoothPathsWindow)