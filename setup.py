import setuptools

with open("README.md", "r") as fh:

    long_description = fh.read()

setuptools.setup(

     name='mwman',
     version='0.1',    
     author="spycrab",
     author_email="spycrab@users.noreply.github.com",
     description="A package manager for MediaWiki",
     long_description=long_description,
     long_description_content_type="text/markdown",
     url="https://github.com/spycrab/mwman",

    install_requires=[
        'colorama',
        'fire',
        'pyyaml',
        'requests'
    ],
    
     entry_points={
         'console_scripts': [
	     'mwman=mwman.application:main',
	]
     },

     packages=setuptools.find_packages(),
     
     package_data={'mwman': ['MWMan.php']},
     include_package_data=True,

     classifiers=[
         "Programming Language :: Python :: 3",
         "License :: OSI Approved :: MIT License",
         "Operating System :: OS Independent",
     ],

 )
