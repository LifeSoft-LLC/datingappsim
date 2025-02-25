import papermill as pm 

while True:
	try:
		pm.execute_notebook("hinge_simulation_test_ver4.ipynb", "/dev/null")
	except Exception as e:
		print(f"Error running backend notebook: {e}")