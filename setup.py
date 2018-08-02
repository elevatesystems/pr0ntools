from distutils.core import setup

with open('README') as file:
    long_description = file.read()

setup(name='pr0ntools',
	version='1.0',
	comment='Integrated circuit reverse engineering research and development',
	description='Integrated circuit reverse engineering research and development',
	long_description = long_description,
	package_dir={
			'pr0ntools': 'pr0ntools',
			'pr0ntools.image': 'pr0ntools/image',
			'pr0ntools.jssim': 'pr0ntools/jssim',
			'pr0ntools.jssim.cif': 'pr0ntools/jssim/cif',
			'pr0ntools.jssim.files': 'pr0ntools/jssim/files',
			'pr0ntools.stitch': 'pr0ntools/stitch',
			'pr0ntools.stitch.pto': 'pr0ntools/stitch/pto',
			'pr0ntools.tile': 'pr0ntools/tile',
			},
	packages=[
			'pr0ntools',
			'pr0ntools.image',
			'pr0ntools.jssim',
			'pr0ntools.jssim.cif',
			'pr0ntools.jssim.files',
			'pr0ntools.stitch',
			'pr0ntools.stitch.pto',
			'pr0ntools.tile',
			],
	scripts=[
			'stitch/pr0nhugin.py',
			'stitch/pr0nmap.py',
			'stitch/pr0npto.py',
			'stitch/pr0nstitchaj.py',
			'stitch/pr0nstitch.py',
			'stitch/pr0ntile.py',
			'stitch/pr0nts.py',
			'stitch/pr0nauto',
			],
	author='John McMaster',
	author_email='JohnDMcMaster@gmail.com',
	url='https://github.com/JohnDMcMaster/pr0ntools/',
)

