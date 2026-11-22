"""Department prefix to TAMU college/school map.

The catalog department index is a flat list, so the college is not on the page.
I built this by hand from the 2026-2027 catalog's college listing. Prefixes I
could not place stay as "Other/Professional" instead of being guessed.
"""

COLLEGE_MAP = {}

def _add(college, prefixes):
    for p in prefixes.split():
        COLLEGE_MAP[p] = college

_add("College of Agriculture and Life Sciences", """
AGCJ AGEC AGLS AGSC AGSM ALEC ALED ANSC BESC BICH BOTN DASC ECCB ENTO FIVS FSTC
GENE HORT HMGT MEPS NUTR PLPA POSC RPTS RWFM SCSC WFSC
""")
_add("College of Architecture", """
ARCH CARC COSC ENDS LAND PLAN URPN URSC VIST VIZA
""")
_add("Mays Business School", """
ACCT ANLY BUAD BUSN ECMT ENTR FINC FINP IBUS ISTM MGMT MKTG SCMT SPBA SPMT
""")
_add("College of Education and Human Development", """
BEFB BESL CEHD CTFB CTSE ECDE ECFB ECHE EDAD EDCI EDHP EHRD EPFB EPSY HDFS HEFB
HLTH INST KINE KNFB MEFB RDNG SEFB SPED TEED TEFB
""")
_add("College of Engineering", """
AERO AREN BAEN BMEN CHEN CLEN CSCE CVEN CYBR DAEN ECEN ENDG ENGR ENGY ENTC ESET
EVEN IDIS ISEN ITDE MEEN MEMA MMET MSEN MTDE MXET NUEN OCEN PETE SENG SPEN SSEN
SYEN
""")
_add("College of Arts and Sciences", """
AALO AFST ANTH ARAB ARSC ARTS ASIA ASTR ATMO CHEM CHIN CLAS COMM DHUM ECON ENGL
EURO FILM FREN GEOG GEOL GEOP GERM GLST HBRW HISP HIST HUMA ITAL JAPN JWST LING
LMAS MATH MODL MUSC OCNG PBSI PERF PHIL PHYS POLS PORT PSYC RELS RUSS SOCI SPAN
STAT THEA WGST ZOOL
""")
_add("College of Geosciences", """
GEOG GEOL GEOP GEOS OCNG WMHS
""")
_add("College of Veterinary Medicine and Biomedical Sciences", """
BIMS VPAR VPAT VLCS VMID VSCS VTMI VTPB VTPP VIBS
""")
_add("School of Public Health", """
HBEH PHEB PHEO PHLT PHPM SOPH
""")
_add("College of Nursing", "NURS NRPR")
_add("College of Pharmacy", "PHAR PHSC")
_add("College of Dentistry", """
AEGD DDHS DDDS DPHS ENDO OBIO OMFP OMFR OMFS ORTH PEDD PERI PROS
""")
_add("School of Medicine", """
AAMD ANES CPSY EMED FSCI HCPI HHUM IMED MCMD MEID MFCM MHUM MPAT MPED MPHY MPIM
MPSY MRAD MSCI NEXT NRSC OBGY SOMS SURG
""")
_add("Bush School of Government and Public Service", "BUSH INTA PSAA")
_add("Galveston Campus", """
GALV MARA MARB MARE MARR MARS MART MASE MAST
""")
_add("General and Interdisciplinary", """
ASCC FYEX HONR ITsv ITSV MLSC MSTC MUST NVSC TAMU TCMG TCMT UGST
""")

DEFAULT_COLLEGE = "Other/Professional"


def college_for(prefix: str) -> str:
    return COLLEGE_MAP.get(prefix.upper(), DEFAULT_COLLEGE)
