wikiBEAGLE
==========

Computes semantic vectors via the BEAGLE algorithm of Jones & Mewhort (2007; plus word-form representation, inspired by Cox, Kachergis, Recchia & Jones, 2011) using random wikipedia pages as a corpus.

Multiple cores can be used by specifying the number of desired cores at the command-line, as in: `python wikiBEAGLE.py 4`

Data is stored in memory (separately for each core) until memory runs low, at which point it is written to file and memory is cleared to start anew.

Quit via `q` key, which will permit wikiBEAGLE to store the data to file and resume where it left off next time you run it.

Use wikiBEAGLEcleaner.py to aggregate all saved files to a single dataset for use in semantic analysis.

Some example semantic analyses are in wikiBEAGLEprobe.py
