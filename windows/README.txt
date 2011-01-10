Install:
Requires ironpython to run, so feel free to install that. 
Also, if this was pulled from Source Depot, there might be some missing files:

SketchCade\MSRecognizers\__init__.py
SketchCade\Observers\__init__.py
SketchCade\Utils\__init__.py
SketchCade\SketchFramework\__init__.py
SketchCade\WindowsLib\__init__.py

They are just empty files for module management, but Source Depot doesn't like the names.

1) Install ironpython
2) Install .Net 4.0 framework
3) Associate *.py files with ipy.exe or ipy64.exe within ironpython install directory.



Running:

4) Run SHETCHSYSTEM.bat or SketchSystem.py
 (Once you have it, just run ipy.exe SketchSystem.py and all should start up just fine.)

