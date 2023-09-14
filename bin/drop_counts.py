#!/usr/bin/env python3

import argparse
import re
from collections import OrderedDict
from pathlib import Path
import sys
from pandas import read_csv, DataFrame
from typing import Set, Dict

SCRIPT_VERSION = "v1.0"
TRANSLATOR = {
    "unstranded": 1,
    "forward": 2,
    "reverse": 3,
}

STANDARD_CHROMOSOMES = [
    "chr1",
    "chr2",
    "chr3",
    "chr4",
    "chr5",
    "chr6",
    "chr7",
    "chr8",
    "chr9",
    "chr10",
    "chr11",
    "chr12",
    "chr13",
    "chr14",
    "chr15",
    "chr16",
    "chr17",
    "chr18",
    "chr19",
    "chr20",
    "chr21",
    "chr22",
    "chrX",
    "chrY",
    "chrM",
]


def get_non_std_genes(gtf: Path) -> Set[str]:
    """Create list of genes not belonging to chr1-21 or chrM"""
    gene_id_regex = re.compile('gene_id "(.+?)"')
    genes_to_exclude = set()
    with open(gtf, "r") as gtf_file:
        for line in gtf_file:
            if line.startswith("#"):
                continue
            if line.split()[0] in STANDARD_CHROMOSOMES:
                continue
            gene_id = re.search(gene_id_regex, line)
            genes_to_exclude.add(gene_id.group(1))
    return genes_to_exclude


def read_star_gene_counts(sample: str, star: Path, strandedness: str) -> Dict:
    """Read gene count file(s) from STAR output to return sample_ids."""
    sample_ids = {}
    gene_ids = {}
    with open(star) as in_tab:
        for line in in_tab:
            if not line.startswith("N_"):
                split_line = line.split()
                gene_id = split_line[0]
                strand = TRANSLATOR[strandedness]
                counts = int(split_line[strand])
                gene_ids[gene_id] = counts
    gene_ids = OrderedDict(sorted(gene_ids.items()))
    sample_ids[sample] = gene_ids
    return sample_ids


def get_counts_from_dict(gene_ids_dict: dict) -> DataFrame:
    """Transform gene ids dict into count_table"""
    one_sample = next(iter(gene_ids_dict))
    gene_list = list(gene_ids_dict[one_sample].keys())
    genes = {gene: [gene_ids_dict[sample][gene] for sample in gene_ids_dict] for gene in gene_list}
    count_table: DataFrame = DataFrame.from_dict(genes, orient="index", columns=gene_ids_dict.keys())
    count_table.index.name = "geneID"
    return count_table


def write_tsv_from_dict(gene_ids_dict: dict, outfile: str, ref_count_file: str, genes_to_exclude: Set[str]) -> None:
    """Transform dictionary into tsv friendly."""
    count_table = get_counts_from_dict(gene_ids_dict)
    if ref_count_file:
        if ref_count_file.endswith(".gz"):
            ref_table = read_csv(ref_count_file, compression="gzip", sep="\t", header=0, index_col=0)
        else:
            ref_table = read_csv(ref_count_file, sep="\t", header=0, index_col=0)
        count_table = count_table.combine_first(ref_table)
    count_table.drop(genes_to_exclude, inplace=True)
    count_table.to_csv(outfile, compression="gzip", sep="\t", header=True)


def parse_args(argv=None):
    """Define and immediately parse command line arguments."""
    parser = argparse.ArgumentParser(
        formatter_class=argparse.MetavarTypeHelpFormatter,
        description="""Generate collated gene counts from each STAR output.""",
    )
    parser.add_argument("--star", type=str, nargs="+", help="*ReadsPerGene.out.tab from STAR", required=True)
    parser.add_argument("--samples", type=str, nargs="+", help="corresponding sample name", required=True)
    parser.add_argument("--strandedness", type=str, nargs="+", help="strandedness of RNA", required=True)
    parser.add_argument("--output", type=str, help="output tsv file name", required=True)
    parser.add_argument("--gtf", type=str, help="Transcript annotation file in gtf format", required=True)
    parser.add_argument("--ref_count_file", type=str, help="Optional reference count set", required=True)
    parser.add_argument("--version", action="version", version=SCRIPT_VERSION)
    return parser.parse_args(argv)


def main(argv=None):
    """Coordinate argument parsing and program execution."""
    args = parse_args(argv)
    master_dict = {}
    for index, sample_id in enumerate(args.samples):
        master_dict.update(
            read_star_gene_counts(sample=sample_id, star=args.star[index], strandedness=args.strandedness[index])
        )

    genes_to_exclude: Set[str] = get_non_std_genes(gtf=args.gtf)
    write_tsv_from_dict(
        gene_ids_dict=master_dict,
        outfile=args.output,
        ref_count_file=args.ref_count_file,
        genes_to_exclude=genes_to_exclude,
    )


if __name__ == "__main__":
    main()
