"""Computes RF-Score features for the PDBbind data set.

Usage:
    compute_rfscore_features.py [-hv] <pdb_list_file> <pdbbind_dir> <output_file> [<blacklist_file>] [--num-cores=<n>]

Arguments:
    pdb_list_file   file containing pdb codes of complexes to use
    pdbbind_dir     top-level directory of the PDBbind data set
    output_file     file to save the computed features to
    blacklist_file  optional file containing PDB codes to skip; some PDB
        structures are known to cause OpenBabel to seg fault

Options:
    -h --help             show this message and exit
    -v --verbose          print progress updates
    --num-cores=<n>  number of cores to use [default: -1]

Computes all RF-Score features as implemented in Open Drug Discovery Toolkit
for specified protein-ligand complexes from the PDBbind data set and saves
the results to the specified file in .csv format.

"""
import pathlib
import pandas as pd

from docopt import docopt
from joblib import delayed, Parallel
from oddt.toolkits import ob
from oddt.scoring import descriptors


def featurise(protein_file, ligand_file):
    """Compute RF-Score features for a protein and a ligand and return the results as a dictionary.

    Args:
        protein_file (str): Name of the .pdb file containing the protein.
        ligand_file (str): Name of the .sdf file containing the ligand.

    Returns:
        features (dict): A dictionary containing the RF-Score features for the protein-ligand complex.
    """

    protein = next(ob.readfile('pdb', protein_file))
    protein.protein = True # DO NOT SKIP THIS or you will be a sad panda
    ligand = next(ob.readfile('sdf', ligand_file))

    # Build RF-Score features
    rfscore_engine = descriptors.close_contacts_descriptor(
            protein=protein,
            cutoff=12,
            ligand_types=[6,7,8,9,15,16,17,35,53],
            protein_types=[6,7,8,16])
    result = {name: value for name, value in zip(rfscore_engine.titles, rfscore_engine.build([ligand])[0])}

    return result


if __name__=='__main__':
    args = docopt(__doc__)
    
    pdb_list_file = args['<pdb_list_file>']
    pdbbind_dir = args['<pdbbind_dir>']
    output_file = args['<output_file>']
    blacklist_file = args['<blacklist_file>']

    verbose = 10 if args['--verbose'] else 0
    n_jobs = int(args['--num-cores'])

    with open(pdb_list_file, 'r') as f:
        pdbs = [l.strip() for l in f]

    # drop any blacklisted PDB codes
    if blacklist_file:
        with open(os.path.join(blacklist_file), 'r') as f:
            blacklist = [line.strip() for line in f]
        pdbs = [pdb for pdb in pdbs if pdb not in blacklist]

    # list protein and ligand pdb/sdf files and compute features
    protein_files = {pdb: str(pathlib.Path(pdbbind_dir, pdb, f'{pdb}_protein.pdb')) for pdb in pdbs}
    ligand_files = {pdb: str(pathlib.Path(pdbbind_dir, pdb, f'{pdb}_ligand.sdf')) for pdb in pdbs}
    with Parallel(n_jobs=n_jobs, verbose=verbose) as parallel:
        results = parallel(delayed(featurise)(protein_files[pdb], ligand_files[pdb]) for pdb in pdbs)

    features = {pdb: result for pdb, result in zip(pdbs, results)}
    features = pd.DataFrame.from_dict(features).T
    features.to_csv(output_file)

