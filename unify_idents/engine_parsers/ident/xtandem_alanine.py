from itertools import repeat

import pandas as pd
import xml.etree.ElementTree as ETree
import multiprocessing as mp
from tqdm import tqdm

from unify_idents.engine_parsers.base_parser import __IdentBaseParser


def _get_single_spec_df(reference_dict, mapping_dict, spectrum):
    spec_records = []
    spec_level_dict = reference_dict.copy()
    spec_level_info = mapping_dict.keys() & spectrum.attrib.keys()
    spec_level_dict.update(
        {mapping_dict[k]: spectrum.attrib[k] for k in spec_level_info}
    )

    if "z" not in spectrum.attrib:
        return None
    spec_title = spectrum.findall('.//**[@label="Description"]')[0].text.split()[0]
    spec_level_dict["Spectrum Title"] = spec_title
    spec_level_dict["Spectrum ID"] = spec_title.split(".")[1]
    # precursor_mh = float(spectrum.attrib["mh"])

    # Iterate children
    for psm in spectrum.findall(".//protein/*/domain"):
        psm_level_dict = spec_level_dict.copy()

        # TODO: Which mh is Exp and which is Calc --> divide by charge
        psm_level_dict["Calc m/z"] = psm.attrib["mh"]
        # psm_level_dict["Exp m/z"] = precursor_mh / int(psm_level_dict["Charge"])

        psm_level_info = mapping_dict.keys() & psm.attrib.keys()
        psm_level_dict.update({mapping_dict[k]: psm.attrib[k] for k in psm_level_info})

        # Record modifications
        mods = []
        for m in psm.findall(".//aa"):
            mass, abs_pos = m.attrib["modified"], m.attrib["at"]
            # abs pos is pos in protein, rel pos is pos in peptide
            rel_pos = int(abs_pos) - int(psm.attrib["start"])
            mods.append(f"{mass}:{rel_pos}")

        psm_level_dict["Modifications"] = mods

        spec_records.append(psm_level_dict)
    return pd.DataFrame(spec_records)


class XTandemAlanine(__IdentBaseParser):
    """Engine parser to unify X!TandemAlanine results.

    Args:
        input_file (str): path to file to unify
        params (dict, optional): parser specific parameters
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.style = "xtandem_style_1"
        tree = ETree.parse(self.input_file)
        self.root = tree.getroot()
        self.reference_dict.update(
            {
                "Raw data location": self.root.attrib["label"]
                .split("models from ")[1]
                .replace("'", ""),
                "Search Engine": "xtandem_alanine",
            }
        )
        self.mapping_dict = {
            v: k
            for k, v in self.param_mapper.get_default_params(style=self.style)[
                "header_translations"
            ]["translated_value"].items()
        }
        self.reference_dict.update({k: None for k in self.mapping_dict.values()})

    @classmethod
    def check_parser_compatibility(cls, file):
        is_xml = file.as_posix().endswith(".xml")
        with open(file.as_posix()) as f:
            head = "".join([next(f) for x in range(10)])
        contains_ref = "tandem-style.xsl" in head

        return is_xml and contains_ref

    def map_mod_names(self, df):
        """Map massshifts to unimod names.

        Args:
            row (dict): dict containing psm based data from engine file

        Returns:
            str: Description
        """
        unique_mods = set().union(*df["Modifications"].apply(set).values)
        unique_mod_masses = {m.split(":")[0] for m in unique_mods}
        potential_names = {
            m: [
                name
                for name in self.mod_mapper.appMass2name_list(
                    round(float(m), 4), decimal_places=4
                )
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
                    in_seq = df["Sequence"].str[int(pos)].isin(
                        self.mod_dict[name]["aa"]
                    ) & df["Modifications"].str.join("|").str.contains(m)
                    if in_seq.sum() != 0:
                        new_mods.loc[in_seq] += f"{name}:{int(pos)+1};"
                    n_term = (~in_seq) & (
                        ("Prot-N-term" in self.mod_dict[name]["position"])
                        & df["Modifications"].str.join("|").str.contains(m)
                    )
                    if n_term.sum() != 0:
                        new_mods.loc[n_term] += f"{name}:0;"
        df["Modifications"] = new_mods.str.rstrip(";")

        return df

    def unify(self):
        with mp.Pool(self.params.get("cpus", mp.cpu_count() - 1)) as pool:
            chunk_dfs = pool.starmap(
                _get_single_spec_df,
                tqdm(
                    zip(
                        repeat(self.reference_dict),
                        repeat(self.mapping_dict),
                        self.root,
                    ),
                    total=len(self.root),
                ),
            )
        chunk_dfs = [df for df in chunk_dfs if not df is None]
        unified_df = pd.concat(chunk_dfs, axis=0, ignore_index=True)
        unified_df["Calc m/z"] = (
            (unified_df["Calc m/z"].astype(float) - self.PROTON)
            / unified_df["Charge"].astype(int)
        ) + self.PROTON
        unified_df = self.map_mod_names(unified_df)

        return unified_df
