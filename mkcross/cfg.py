import multiprocessing
import pathlib

# TODO move mkdir to cli parser?
dlpath = pathlib.Path("./dist").resolve()
dlpath.mkdir(parents=True, exist_ok=True)
srcpath = pathlib.Path("./srcs").resolve()
srcpath.mkdir(parents=True, exist_ok=True)
buildpath = pathlib.Path("./build").resolve()
buildpath.mkdir(parents=True, exist_ok=True)
outputpath = pathlib.Path("./out").resolve()
outputpath.mkdir(parents=True, exist_ok=True)

makeopts = [f"-j{multiprocessing.cpu_count() + 1}"]
