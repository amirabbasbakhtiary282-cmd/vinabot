from setuptools import setup, find_packages

setup(
    name='vina-ai',
    version='1.0.0',
    author='Vina Team',
    author_email='vina@vinabot.org',
    description='دستیار هوش مصنوعی شخصی وینا',
    packages=find_packages(),
    python_requires='>=3.8',
    install_requires=[
        'kivy>=2.3.0',
        'vosk>=0.3.45',
        'requests>=2.28.0',
        'beautifulsoup4>=4.11.0',
        'numpy>=1.23.0',
    ],
    classifiers=[
        'Development Status :: 4 - Beta',
        'Intended Audience :: End Users/Desktop',
        'Operating System :: Android',
        'Topic :: Communications :: Chat',
        'Topic :: Scientific/Engineering :: Artificial Intelligence',
    ],
    entry_points={
        'console_scripts': [
            'vina=main:VinaApp.run',
        ],
    },
)
