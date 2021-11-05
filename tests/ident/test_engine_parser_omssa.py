#!/usr/bin/env python
from pathlib import Path
from unify_idents.unify import Unify
from unify_idents.engine_parsers.ident.omssa_2_1_9_parser import OmssaParser
import pytest


def test_engine_parsers_omssa_init():
    input_file = (
        Path(__file__).parent.parent
        / "data"
        / "test_Creinhardtii_QE_pH11_omssa_2_1_9.csv"
    )
    rt_lookup_path = Path(__file__).parent.parent / "data" / "_ursgal_lookup.csv.bz2"
    db_path = (
        Path(__file__).parent.parent / "data" / "test_Creinhardtii_target_decoy.fasta"
    )

    parser = OmssaParser(
        input_file,
        params={
            "rt_pickle_name": rt_lookup_path,
            "database": db_path,
            "modifications": [
                {
                    "aa": "M",
                    "type": "opt",
                    "position": "any",
                    "name": "Oxidation",
                },
                {
                    "aa": "C",
                    "type": "fix",
                    "position": "any",
                    "name": "Carbamidomethyl",
                },
                {
                    "aa": "*",
                    "type": "opt",
                    "position": "Prot-N-term",
                    "name": "Acetyl",
                },
            ],
            "omssa_mod_dir": Path(__file__).parent.parent / "data",
        },
    )


def test_engine_parsers_omssa_file_matches_parser():
    input_file = (
        Path(__file__).parent.parent
        / "data"
        / "test_Creinhardtii_QE_pH11_omssa_2_1_9.csv"
    )
    assert OmssaParser.check_parser_compatibility(input_file) is True


def test_engine_parsers_omssa_unify():
    input_file = (
        Path(__file__).parent.parent
        / "data"
        / "test_Creinhardtii_QE_pH11_omssa_2_1_9.csv"
    )
    rt_lookup_path = Path(__file__).parent.parent / "data" / "_ursgal_lookup.csv.bz2"
    db_path = (
        Path(__file__).parent.parent / "data" / "test_Creinhardtii_target_decoy.fasta"
    )

    parser = OmssaParser(
        input_file,
        params={
            "rt_pickle_name": rt_lookup_path,
            "database": db_path,
            "modifications": [
                {
                    "aa": "M",
                    "type": "opt",
                    "position": "any",
                    "name": "Oxidation",
                },
                {
                    "aa": "C",
                    "type": "fix",
                    "position": "any",
                    "name": "Carbamidomethyl",
                },
                {
                    "aa": "*",
                    "type": "opt",
                    "position": "Prot-N-term",
                    "name": "Acetyl",
                },
            ],
            "omssa_mod_dir": Path(__file__).parent.parent / "data",
        },
    )
    first_row = parser.unify().iloc[0, :]
    assert first_row["Raw data location"] == "test_Creinhardtii_QE_pH11"
    assert first_row["Sequence"] == "ALAMEWGPFPRLMVVACNDAINVCRK"
    assert set(first_row["Modifications"].split(";")) == {
        "Oxidation:4",
        "Carbamidomethyl:24",
        "Carbamidomethyl:17",
    }
    assert first_row["Search Engine"] == "omssa_2_1_9"


def test_engine_parsers_omssa_is_iterable():
    input_file = (
        Path(__file__).parent.parent
        / "data"
        / "test_Creinhardtii_QE_pH11_omssa_2_1_9.csv"
    )
    rt_lookup_path = (
        Path(__file__).parent.parent / "data" / "BSA1_ursgal_lookup.csv.bz2"
    )
    db_path = (
        Path(__file__).parent.parent / "data" / "test_Creinhardtii_target_decoy.fasta"
    )

    parser = OmssaParser(
        input_file,
        params={
            "rt_pickle_name": rt_lookup_path,
            "database": db_path,
            "modifications": [
                {
                    "aa": "M",
                    "type": "opt",
                    "position": "any",
                    "name": "Oxidation",
                },
                {
                    "aa": "C",
                    "type": "fix",
                    "position": "any",
                    "name": "Carbamidomethyl",
                },
                {
                    "aa": "*",
                    "type": "opt",
                    "position": "Prot-N-term",
                    "name": "Acetyl",
                },
            ],
            "omssa_mod_dir": Path(__file__).parent.parent / "data",
            "Raw data location": "/Users/cellzome/Dev/Gits/Ursgal/ursgal_master/example_data/test_Creinhardtii_QE_pH11.mgf",
        },
    )
    df = parser.unify()
    assert len(df) == 179


def test_engine_parsers_omssa_next():
    input_file = (
        Path(__file__).parent.parent
        / "data"
        / "test_Creinhardtii_QE_pH11_omssa_2_1_9.csv"
    )
    rt_lookup_path = Path(__file__).parent.parent / "data" / "_ursgal_lookup.csv.bz2"
    db_path = (
        Path(__file__).parent.parent / "data" / "test_Creinhardtii_target_decoy.fasta"
    )

    parser = Unify(
        input_file,
        params={
            "rt_pickle_name": rt_lookup_path,
            "database": db_path,
            "modifications": [
                {
                    "aa": "M",
                    "type": "opt",
                    "position": "any",
                    "name": "Oxidation",
                },
                {
                    "aa": "C",
                    "type": "fix",
                    "position": "any",
                    "name": "Carbamidomethyl",
                },
                {
                    "aa": "*",
                    "type": "opt",
                    "position": "Prot-N-term",
                    "name": "Acetyl",
                },
            ],
            "omssa_mod_dir": Path(__file__).parent.parent / "data",
            "Raw data location": "/Users/cellzome/Dev/Gits/Ursgal/ursgal_master/example_data/test_Creinhardtii_QE_pH11.mgf",
        },
    )
    df = parser.get_dataframe()
    row = df.iloc[0, :]
    assert row["Sequence"] == "ALAMEWGPFPRLMVVACNDAINVCRK"
    assert row["Modifications"] == "Oxidation:4;Carbamidomethyl:17;Carbamidomethyl:24"
    assert (
        row["Raw data location"]
        == "/Users/cellzome/Dev/Gits/Ursgal/ursgal_master/example_data/test_Creinhardtii_QE_pH11.mzML"
    )
    assert row["Charge"] == 4
    assert float(row["OMSSA:pvalue"]) == pytest.approx(0.000166970504409832)
    assert float(row["Calc mass"]) == pytest.approx(3033.491)
    assert float(row["Calc m/z"]) == pytest.approx(759.38002646677)
