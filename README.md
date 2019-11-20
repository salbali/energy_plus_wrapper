energy+ wrapper
===============

This little library has been written in order to run energy+ simulation
in linux and windows in a thread-safe way.

The main goal is to ensure a stable behaviour across platform and
version, and to make the link between the e+ building model tools
written in python and the different analysis and optimization tools.

Install
=======

For now, the package is available on PyPI, and via the github repo.

``` {.sourceCode .shell}
pip install energyplus-wrapper
pip install git+git://github.com/locie/energy_plus_wrapper.git
```

for the requirements.

Usage
=====

There is two main classes in the library: the EPlusRunner and the Simulation.

The first one is linked with the EnergyPlus local installation and allow to run
one or many simulation. It also ensure the compatibility between the executable
and the IDF file.

The later is generated with the `runner.run_one` and `runner.run_many`. It
contains the EnergyPlus simulation reports and results.

A small utility routine `ensure_eplus_root` allow to automatically download,
extract and install EnergyPlus (but only for linux for now).

```python
from energyplus_wrapper import EPlusRunner, ensure_eplus_root

eplus_root = ensure_eplus_root("http://url/to/eplus/install.sh")
# or
eplus_root = "path/to/energyplus/install/dir"

runner = EPlusRunner(eplus_root)
simulation = runner.run("my/idf/file.idf", "my/weather/file.epw")
print(simulation.reports)
print(simulation.time_series)
```

The runner.run is multi-process safe, allowing to run multiple EnergyPlus
simulation at the same time.

The method `runner.run_many` allow to run multiple simulation at the same
time. It uses `joblib.parallel` under the hood : how the simulation are
ran and how many CPU are used can be controlled by `joblib.parallel_backend`

```python
from energyplus_wrapper import EPlusRunner, ensure_eplus_root

eplus_root = ensure_eplus_root("http://url/to/eplus/install.sh")
# or
eplus_root = "path/to/energyplus/install/dir"

runner = EPlusRunner(eplus_root)

samples = {"sim01": ("idf01.idf", "weather01.epw"),
           "sim02": ("idf02.idf", "weather01.epw"),
           "sim03": ("idf03.idf", "weather02.epw"),
           "sim04": ("idf04.idf", "weather02.epw")}

# run on 4 CPU
with joblib.parallel_backend("loky", n_jobs=4):
    sims = runner.run_many(samples)

print(sims.keys())
```

`run_one`, `run_many` common mecanism
-------------------------------------

*backup*

According to the `backup_strategy`, the runner can save the
files generated by EnergyPlus in the `backup` folder. It can
save the files `'always'`, `'on_error'`, or never (with `None`).

*version check*

According to `version_mismatch_action`, a mismatch between the
e+ executable and the idf file version will `raise` an error,
`warn` the user or be `ignore`d.

*custom post-process*

You can provide a custom simulation post process. By default,
the file `eplus-table.htm` is parsed and put in the
`simulation.reports` attribute, and all the csv files generated
by the run are parsed and put in `simulation.time_series`.

For example, you could save all the files generated by the simulation with

```python
from path import Path
import zipfile

archive_folder = Path("./archive/").abspath()

def save_and_compress(simulation):
    with zipfile.ZipFile(archive_folder / f"{simulation.name}.gz", "w", zipfile.ZIP_DEFLATED) as zip_handler:
        for file in simulation.working_dir.files("*"):
            zip_handler.write(file)

runner.run_one(idf, wf, custom_process=save_and_compress)
```