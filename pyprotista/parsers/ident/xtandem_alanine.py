"""Engine parser."""

import pandas as pd
import regex as re
from loguru import logger
import xml.etree.ElementTree as etree
from pyprotista.parsers.ident_base_parser import IdentBaseParser


def get_xml_data(file, mapping_dict):
    """Iterate over file to get information on specs.

    Args:
        file (str): path to input file
        mapping_dict (dict): mapping of engine level column names to pyprotista unified column names

    Returns:
        chunks (list): spectrum information
        search_engine (str): file version
    """
    chunks = []

    # Temporary variables, get overwritten multiple times during iteration
    results = {}
    domains = []
    mods = []
    aa_mods = []

    for event, entry in etree.iterparse(file):
        entry_tag = entry.tag

        if entry_tag == ("aa"):
            aa_mods.append({"mass": entry.attrib["modified"], "at": entry.attrib["at"]})
        elif entry_tag == ("domain"):
            for i in list(entry.attrib):
                if i in mapping_dict:
                    results.update({mapping_dict[i]: entry.attrib[i]})
            for aa in aa_mods:
                mass = aa["mass"]
                at = aa["at"]
                start = entry.attrib["start"]
                rel_pos = int(at) - int(start)
                mods.append(f"{mass}:{rel_pos}")
            results["modifications"] = mods
            results["calc_mz"] = entry.attrib["mh"]
            mods = []
            aa_mods = []
            domains.append(results)
            results = {}
        elif entry_tag == ("note"):
            if entry.attrib["label"] == "Description":
                results.update({"spectrum_title": entry.text.split()[0]})
                results.update({"spectrum_id": entry.text.split(".")[-3]})
            elif entry.attrib["label"] == "process, version":
                search_engine = (
                    "xtandem_"
                    + re.search(r"(?<=Tandem )\w+", entry.text).group().lower()
                )
        elif entry_tag == ("group"):
            if "id" in entry.attrib:
                for i in list(entry.attrib):
                    if i in mapping_dict:
                        results.update({mapping_dict[i]: entry.attrib[i]})
                for dom in domains:
                    dom.update(results)
                    chunks.append(dom)
                domains = []
                results = {}
    return chunks, search_engine


class XTandemAlanine_Parser(IdentBaseParser):
    """File parser for X!Tandem Alanine."""

    def __init__(self, *args, **kwargs):
        """Initialize parser.

        Reads in data file and provides mappings.
        """
        super().__init__(*args, **kwargs)
        self.style = "xtandem_style_1"
        tree = etree.parse(self.input_file)
        self.root = tree.getroot()
        self.mapping_dict = {
            v: k
            for k, v in self.param_mapper.get_default_params(style=self.style)[
                "header_translations"
            ]["translated_value"].items()
        }

    @classmethod
    def check_parser_compatibility(cls, file):
        """Assert compatibility between file and parser.

        Args:
            file (str): path to input file

        Returns:
            bool: True if parser and file are compatible

        """
        is_xml = file.as_posix().endswith(".xml")
        with open(file.as_posix()) as f:
            try:
                head = "".join([next(f) for _ in range(10)])
            except StopIteration:
                head = ""
        contains_ref = "tandem-style.xsl" in head

        return is_xml and contains_ref

    def map_mod_names(self, df):
        """Map modifications on corresponding sequences.

        Args:
            df (pd.DataFrame): spectrum information

        Returns:
            df (pd.DataFrame): added modification column

        """
        unique_mods = set().union(*df["modifications"].apply(set).values)
        unique_mod_masses = {m.split(":")[0] for m in unique_mods}
        potential_names = {
            m: [
                name
                for name in self.mod_mapper.mass_to_names(float(m), decimals=4)
                if name in self.mod_dict
            ]
            for m in unique_mod_masses
        }
        mod_translation = {}
        new_mods = pd.Series("", index=df.index)
        for m in unique_mods:
            mass, pos = m.split(":")
            potential_mods = potential_names[mass]
            if len(potential_mods) == 0:
                mod_translation[m] = None
            else:
                for name in potential_mods:
                    # TODO: Is position 'any' respected here
                    in_seq = df["sequence"].str[int(pos)].isin(
                        self.mod_dict[name]["aa"]
                    ) & df["modifications"].str.join("|").str.contains(m)
                    n_term = (~in_seq) & (
                        (
                            ("N-term" in self.mod_dict[name]["position"])
                            | ("Prot-N-term" in self.mod_dict[name]["position"])
                        )
                        & df["modifications"].str.join("|").str.contains(m)
                    )
                    if in_seq.sum() != 0:
                        new_mods.loc[in_seq] += f"{name}:{int(pos)+1};"
                    elif n_term.sum() != 0:
                        new_mods.loc[n_term] += f"{name}:0;"
                    else:
                        logger.error(f"Modification {name} could not be mapped.")
                        raise KeyError
        df["modifications"] = new_mods.str.rstrip(";")

        return df

    def unify(self):
        """
        Primary method to read and unify engine output.

        Returns:
            self.df (pd.DataFrame): unified dataframe
        """
        chunks, search_engine = get_xml_data(self.input_file, self.mapping_dict)
        self.df = pd.DataFrame(chunks)
        self.df["search_engine"] = search_engine
        self.df["exp_mz"] = None
        self.df["calc_mz"] = (
            (self.df["calc_mz"].astype(float) - self.PROTON)
            / self.df["charge"].astype(int)
        ) + self.PROTON
        self.df = self.map_mod_names(self.df)
        self.process_unify_style()

        return self.df
