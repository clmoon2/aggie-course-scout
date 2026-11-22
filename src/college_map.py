"""Department prefix to TAMU college/school map.

Built from the 2026-2027 catalog program index. Prefixes the index does not
place stay "Other/Professional" instead of being guessed.
"""

COLLEGE_MAP = {}


def _add(college, prefixes):
    for p in prefixes.split():
        COLLEGE_MAP[p] = college


_add("College of Agriculture and Life Sciences", """
AGCJ AGEC AGLS AGSC AGSM ALEC ALED ANSC BESC BICH BOTN DASC ECCB ENTO FIVS
FSTC GENE HORT HMGT MEPS MICR NUTR PLPA POSC RPTS RWFM SCSC WFSC
""")
_add("College of Architecture", "ARCH CARC COSC ENDS LAND LDEV PLAN URPN URSC")
_add("Mays Business School", """
ACCT ANLY BUAD BUSN ECMT ENTR FINC FINP IBUS ISTM MGMT MKTG SCMT SPBA
""")
_add("College of Education and Human Development", """
ATTR BEFB BESL CEHD CPSY CTFB CTSE DCED ECDE ECFB ECHE EDAD EDCI EDHP EHRD EPFB
EPSY HDFS HEFB INST KINE KNFB LDTC LTPS MEFB RDNG SEFB SPED SPMT SPSY TEED TEFB
""")
_add("College of Engineering", """
AERO AREN BAEN BMEN CHEN CLEN CSCE CVEN CYBR DAEN ECEN ENDG ENGR ENGY ENTC ESET
EVEN IDIS ISEN ITDE MEEN MEMA MMET MSEN MTDE MXET NUEN OCEN PETE SENG SPEN SSEN
SYEN
""")
_add("College of Arts and Sciences", """
AALO AFST ANTH ARAB ARSC ASIA ASTR ATMO BIOL CHEM CHIN CLAS COMM DHUM ECON ENGL
ENSS ENST ESST EURO FREN GEOG GEOL GEOP GEOS GERM GLST HBRW HISP HIST HUMA ITAL
JAPN JOUR JWST LING LMAS MATH MODL OCNG PBSI PHIL PHYS PORT PSYC RELS RUSS SOCI
SPAN STAT WGST ZOOL
""")
_add("College of Performance, Visualization and Fine Arts", """
ARTS FILM MUSC PERF PVFA THEA VIST VIZA
""")
_add("College of Veterinary Medicine and Biomedical Sciences", """
BIMS VLCS VMID VPAR VPAT VSCS VTMI VTPB VTPP VIBS
""")
_add("School of Public Health", """
HBEH HLTH PHEB PHEO PHLT PHPM SOPH WMHS
""")
_add("College of Nursing", "FORS NURS NRPR")
_add("College of Pharmacy", "PHAR PHSC")
_add("College of Dentistry", """
AEGD DDHS DDDS DPHS ENDO OBIO OMFP OMFR OMFS ORTH PEDD PERI PROS
""")
_add("School of Medicine", """
AAMD ANES EMED FSCI HCPI HHUM IMED MCMD MEID MFCM MHUM MPAT MPED MPHY MPIM
MPSY MRAD MSCI NEXT NRSC OBGY SURG
""")
_add("Bush School of Government and Public Service", "BUSH INTA POLS PSAA")
_add("School of Military Sciences", "AERS MLSC NVSC SOMS")
_add("School of Law", "LAW")
_add("Galveston Campus", """
FSCI GALV MARA MARB MARE MARR MARS MART MASC MASE MAST
""")
_add("General and Interdisciplinary", """
ASCC FYEX HONR ITsv ITSV MSTC MUST TAMU TCMG TCMT UGST
""")

DEFAULT_COLLEGE = "Other/Professional"


def college_for(prefix: str) -> str:
    return COLLEGE_MAP.get(prefix.upper(), DEFAULT_COLLEGE)
