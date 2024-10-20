#!/usr/bin/env python3

import argparse
from pandas import DataFrame, read_csv, concat
import pyreadr

SCRIPT_VERSION = "v1.0"
GENE_PANEL_HEADER = ["chromosome", "gene_start", "gene_stop", "hgnc_id", "hgnc_symbol"]
GENE_PANEL_COLUMNS_TO_KEEP = ["hgnc_symbol", "hgnc_id"]


def get_top_hits(sample_id: str, df_results_family_aberrant_expression: DataFrame) -> DataFrame:
    """
    Filter results to get only those with the id provided.
    If there are >= 20 hits it will output all of them.
    If there are less than 20 hits, it will output the 20 with the lowest p-value.
    """
    df_id: DataFrame = df_results_family_aberrant_expression[
        df_results_family_aberrant_expression["sampleID"] == sample_id
    ]
    if sum(df_id["aberrant"] == "True") >= 20:
        return df_id
    df_id = df_id.sort_values(by=["pValue"]).reset_index()
    return df_id[:20]


def annotate_with_hgnc(df_family_aberrant_expression_top_hits: DataFrame, out_drop_gene_name: str) -> DataFrame:
    """Annotate results from DROP Aberrant Expression with hgnc ids."""
    df_genes: DataFrame = read_csv(out_drop_gene_name)
    df_genes.rename(columns={"gene_name": "hgncSymbol"}, inplace=True)
    return df_genes.merge(df_family_aberrant_expression_top_hits, left_on="gene_id", right_on="geneID")


def filter_by_gene_panel(df_family_top_hits: DataFrame, gene_panel: str, module_name: str) -> DataFrame:
    """Filter out from results any gene that is not present in the provided gene panel."""
    if gene_panel != "None":
        df_panel: DataFrame = read_csv(
            gene_panel, sep="\t", names=GENE_PANEL_HEADER, header=None, comment="#", index_col=False
        )
        df_family_top_hits = df_family_top_hits.loc[df_family_top_hits["hgncSymbol"].isin(df_panel["hgnc_symbol"])]
        df_clinical: DataFrame = df_panel[GENE_PANEL_COLUMNS_TO_KEEP].merge(
            df_family_top_hits, left_on="hgnc_symbol", right_on="hgncSymbol"
        )
        df_clinical = df_clinical.drop(columns=["hgnc_symbol"])
        file_name = f"{module_name}_provided_samples_top_hits_filtered.tsv"
        df_clinical.to_csv(file_name, sep="\t", index=False, header=True)


def filter_outrider_results(
    samples: list, gene_panel: str, out_drop_aberrant_expression_rds: str, out_drop_gene_name: str
):
    """
    Filter results to get only those from the sample(s) provided.
    If there are >= 20 hits per sample it will output all of them.
    If there are less than 20 hits per sample, it will output the 20 with the lowest p-value.
    The results will be annotated with hgnc id.
    Two tsvs will be outputed:
        - One filtered to keep gense in the gene panel (if provided).
        - Another that is unfilterd.
    """
    rds_aberrant_expression = pyreadr.read_r(out_drop_aberrant_expression_rds)
    df_results_aberrante_expression: DataFrame = rds_aberrant_expression[None]
    # Keep only samples provided to tomte
    df_results_family_aberrant_expression: DataFrame = df_results_aberrante_expression.loc[
        df_results_aberrante_expression["sampleID"].isin(samples)
    ]
    df_family_aberrant_expression_top_hits = DataFrame()
    for id in samples:
        df_sample_aberrant_expression_top_hits = get_top_hits(id, df_results_family_aberrant_expression)
        df_family_aberrant_expression_top_hits = concat(
            [df_family_aberrant_expression_top_hits, df_sample_aberrant_expression_top_hits],
            ignore_index=True,
            sort=False,
        )
        df_family_aberrant_expression_top_hits = df_family_aberrant_expression_top_hits.drop(columns=["index"])
    df_family_annotated_aberrant_expression_top_hits = annotate_with_hgnc(
        df_family_aberrant_expression_top_hits, out_drop_gene_name
    )
    df_family_annotated_aberrant_expression_top_hits.to_csv(
        "OUTRIDER_provided_samples_top_hits.tsv", sep="\t", index=False, header=True
    )
    filter_by_gene_panel(df_family_annotated_aberrant_expression_top_hits, gene_panel, "OUTRIDER")


def filter_fraser_result(samples: list, gene_panel: str, out_drop_aberrant_splicing_tsv: str):
    """
    Filter results to get only those from the sample(s) provided.
    Two tsvs will be outputed:
        - One filtered to keep gense in the gene panel (if provided).
        - Another that is unfilterd.
    """
    df_results_aberrant_splicing: DataFrame = read_csv(out_drop_aberrant_splicing_tsv, sep="\t")
    # Keep only samples provided to tomte
    df_results_family_aberrant_splicing: DataFrame = df_results_aberrant_splicing.loc[
        df_results_aberrant_splicing["sampleID"].isin(samples)
    ]
    df_results_family_aberrant_splicing.to_csv(
        "FRASER_provided_samples_top_hits.tsv", sep="\t", index=False, header=True
    )
    filter_by_gene_panel(df_results_family_aberrant_splicing, gene_panel, "FRASER")


def parse_args(argv=None):
    """Define and immediately parse command line arguments."""
    parser = argparse.ArgumentParser(
        formatter_class=argparse.MetavarTypeHelpFormatter,
        description="""Filter DROP results to keep only the patient samples and the genes within the panel if provided""",
    )
    parser.add_argument(
        "--samples",
        type=str,
        nargs="+",
        help="corresponding samples name",
        required=True,
    )
    parser.add_argument(
        "--gene_panel",
        type=str,
        default="None",
        help="Path to gene panel for filtering",
        required=False,
    )
    parser.add_argument(
        "--drop_ae_rds",
        type=str,
        default="None",
        help="Path to RDS output from DROP Aberrant Expression",
        required=False,
    )
    parser.add_argument(
        "--out_drop_gene_name",
        type=str,
        default="None",
        help="Path to gene name annotion, output from DROP Aberrant Expression",
        required=False,
    )
    parser.add_argument(
        "--out_drop_as_tsv",
        type=str,
        default="None",
        help="Path to tsv output from DROP Aberrant Splicing",
        required=False,
    )
    parser.add_argument(
        "--version",
        action="version",
        version=SCRIPT_VERSION,
    )
    return parser.parse_args(argv)


def main():
    """Coordinate argument parsing and program execution."""
    args = parse_args()
    filter_outrider_results(
        samples=args.samples,
        gene_panel=args.gene_panel,
        out_drop_aberrant_expression_rds=args.drop_ae_rds,
        out_drop_gene_name=args.out_drop_gene_name,
    )
    filter_fraser_result(
        samples=args.samples, gene_panel=args.gene_panel, out_drop_aberrant_splicing_tsv=args.out_drop_as_tsv
    )


if __name__ == "__main__":
    main()
