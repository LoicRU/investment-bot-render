"""
Univers complet — 500+ tickers
Small caps, micro caps, mid caps sous 50$
Organisés par secteur pour rotation équitable
"""

UNIVERSE = {

    "IA_TECH": [
        "SOUN","BBAI","IONQ","QBTS","RGTI","QUBT","ARQT","DAVE",
        "AITX","AGEN","INPX","VSBLTY","DTST","NNOX","RCAT",
        "BTBT","BTDR","WULF","CIFR","MARA","CLSK","RIOT","IREN",
        "AUVI","TPVG","KALI","GFAI","GXAI","AEYE","AIXI",
    ],

    "SEMICONDUCTEURS": [
        "CRDO","AEHR","WOLF","ENVX","AAOI","CEVA","FORM","ACLS",
        "ONTO","ICHR","UCTT","AZTA","MKSI","CAMT","AEIS","AMBA",
        "ALGM","AXTI","DIOD","IMOS","MPWR","NXPI","PSEM","SLAB",
        "SWKS","TSEM","VSEC","XPERI","COHU","LSCC","MCHP",
    ],

    "SAAS_CLOUD": [
        "GTLB","CFLT","DOCN","MGNI","TBLA","TASK","BRZE","MKTW",
        "ALKT","ALRM","APPF","APPN","AVPT","BASE","BIGC","BLKB",
        "BOX","CARG","CCSI","CDAY","CGNT","CLOU","CLPS","CMPR",
        "CNXC","COUP","CWAN","DCBO","DOMO","DOCU","DV","ENFN",
        "ESTC","EVCM","EVBG","FROG","FTNT","GDRX","GENI","GPRE",
        "HIMS","HRTH","INFA","INST","JAMF","KALA","LPSN","MDLA",
        "MNDY","MNTV","NCNO","NTNX","OMCL","OPEN","PAYC","PCTY",
        "PING","PLTK","PMVP","PRGS","PSFE","PTON","PWSC","QMCO",
        "RAMP","RNST","RSKD","RXST","SMAR","SNCR","SPOK","SPSC",
        "SPRK","SQSP","STEM","SUMO","TDUP","TENB","TOST","TTGT",
        "TUYA","TWLO","TZOO","UPWK","VERA","VNET","VRNT","VTEX",
        "WDAY","WEX","XMTR","YEXT","ZI","ZETA","ZUO",
    ],

    "BIOTECH_SANTE": [
        "RXRX","NTLA","BEAM","EDIT","VERV","TMDX","ACAD","ALDX",
        "ALEC","ALGS","ALKT","ALLK","ALNY","ALVR","AMPE","AMRS",
        "AMTI","ANAB","ANIK","ANNX","APLS","APRE","APTX","ARCT",
        "ARGT","ARMO","ARNA","ARQT","ARVN","ASND","ATAX","ATCX",
        "ATDX","ATRC","ATRM","ATRS","ATXI","AUPH","AVDL","AVEO",
        "AVXL","AXSM","AYLA","BCAB","BCDA","BCEL","BCLI","BDSI",
        "BEAM","BGNE","BIOL","BLFS","BLPH","BLUE","BMRN","BNGO",
        "BNOX","BPMC","BPTH","BRKL","BSGM","BTAI","BVXV","BYFC",
        "CABA","CAPR","CARA","CARE","CCRN","CDTX","CERE","CGEM",
        "CHRS","CLBS","CLNN","CLRB","CLVS","CMPS","CNCE","CNSP",
        "COCP","CODX","CORT","CPHC","CPIX","CRBU","CRIS","CRNX",
        "CRSP","CTMX","CTNM","CVAC","CXDO","CYRX","DARE","DCPH",
        "DERM","DMTK","DNLI","DNUT","DOSE","DRRX","DVAX","DYAI",
        "ECOR","EIDX","ELOX","ENLV","ENSG","ENVB","EPZM","ERAS",
        "ETON","ETNB","EVAX","EVFM","EVGN","EVLO","EVOK","EXAI",
        "FATE","FBIO","FDMT","FGEN","FOLD","FRTX","FULC","GALT",
        "GBIO","GCBC","GDRX","GERN","GGUS","GHDX","GLMD","GLPG",
        "GLSI","GMAB","GNFT","GOSS","GOVX","GPMT","GRTX","GRTS",
        "GRVI","GTHX","HALO","HBIA","HCWB","HGEN","HLTH","HMPT",
        "HOOK","HRTX","HSTO","HTBX","HUMA","HYPR","IBRX","ICAD",
        "IDEX","IDYA","IMAB","IMCR","IMGO","IMNN","IMTX","IMVT",
        "IMXI","INAB","INFU","INMD","INVA","IPSC","IRDM","IRWD",
        "ISEE","ISPC","ITIC","ITRI","JAKK","JANX","JAZZ","JNCE",
        "KALA","KALV","KDNY","KNTE","KPTI","KRYS","KTRA","KYMR",
        "LCTX","LGND","LKFN","LMNL","LNTH","LRMR","LSAQ","LXRX",
        "LYRA","MBRX","MCVT","MDGL","MDWD","MEIP","MESO","MGTX",
        "MIRM","MNKD","MNMD","MNOV","MNSB","MODN","MOTS","MRNA",
        "MRSN","MRTX","MRUS","MSRT","MTEM","MTEX","MTTR","NAOV",
        "NBIX","NBTX","NCNA","NEOS","NKGN","NKTR","NLSP","NMIH",
        "NRIX","NSGN","NTGR","NTRA","NUVL","NVAX","NVCR","NVRO",
        "NXGN","NXST","OMER","ONCR","ONCT","ONCY","ONMD","OPCH",
        "OPTN","OSHA","OVID","OXSQ","PAVM","PCVX","PDFS","PHAT",
        "PHVS","PIXY","PLRX","PMVP","PNTM","POET","PRTK","PRTS",
        "PTGX","PTLO","PTVCA","PVAC","QURE","RARE","RCKT","RCUS",
        "RDUS","RGEN","RIGL","RKTA","RLMD","RMTI","RPRX","RRBI",
        "RRGB","RSSS","RSVR","RUBY","RXMD","RYTM","SAGE","SALT",
        "SANA","SAVA","SCPH","SEER","SELB","SENS","SERA","SESN",
        "SGMO","SHBI","SHOT","SIGA","SILK","SINT","SIOX","SLNO",
        "SLRX","SMMT","SNAX","SNDX","SNSE","SPPI","SRPT","SRTX",
        "SSYS","STAB","STOK","STRO","STSA","SURF","SVRA","SVVC",
        "SYRS","TALK","TBPH","TDOC","TELA","TGTX","THMO","THTX",
        "TLRY","TNXP","TPIC","TPTX","TRIL","TRKA","TROX","TRPX",
        "TRVN","TTOO","TYME","UCBI","UGRO","ULUS","UMAC","UNFI",
        "URGN","VAXX","VCNX","VCYT","VERV","VGFC","VKTX","VLCN",
        "VNDA","VNET","VRAY","VRCA","VRDN","VRNA","VSTM","VTAK",
        "VTNR","VXRT","VYGR","WELL","WLFC","WORX","WPRT","XBIT",
        "XCUR","XENE","XENT","XERS","XFOR","XLRN","XNCR","XOMA",
        "XTLB","XXII","YMAB","YRIV","ZAFG","ZEAL","ZEPP","ZFOX",
        "ZLAB","ZNTH","ZSAN","ZTEC","ZURA","ZVRA","ZYME","ZYXI",
    ],

    "SPACE_DEFENCE": [
        "RKLB","ASTS","ACHR","JOBY","LILM","SPIR","MNTS","ASTR",
        "VORB","BKSY","KTOS","AVAV","MAXR","SATL","GSAT","OSAT",
        "SPCE","RDW","ACEL","ARAY","ARKO","ARQQ","CODA","CODA",
        "IRIW","LONN","NRGV","NVTS","ORMP","SPGX","TZPS",
    ],

    "FINTECH": [
        "AFRM","UPST","SOFI","DAVE","MGRM","RELY","OPFI","LMND",
        "HIFS","IIPR","INBK","INFU","INSG","ISTR","JFIN","KREF",
        "LADR","LCII","LGIH","LNDC","LOAN","LPRO","MBIN","MCBC",
        "MGYR","MNSB","NBTB","NFBK","NKSH","NMFC","NMLH","NMRK",
        "NNBR","NOAL","NRDS","NRXS","NSTS","NWIN","OBNK","OCFC",
        "OCSL","OFED","OFST","OFSSH","OHPA","OLPX","OMAB","OMER",
        "OMEX","OMGA","OMNIQ","ONBK","ONDS","ONFO","ONIC","ONMD",
        "OPEN","OPHC","OPOF","OPRA","OPRT","OPSM","OQAL","ORBN",
        "ORGO","ORGS","ORIC","ORKT","ORLY","ORMP","ORMT","ORPH",
        "ORRF","ORTX","OSBC","OSEA","OSIS","OSMT","OSPR","OSPT",
        "OSST","OSTK","OSTR","OSUR","OSXB","OTLK","OTMO","OTNK",
    ],

    "ENERGIE_PROPRE": [
        "ARRY","STEM","FLNC","NOVA","OPAL","GDEV","SEDG","ENPH",
        "FCEL","PLUG","BLNK","CHPT","EVGO","WKHS","NKLA","HYLN",
        "CWEN","CLNE","AMRC","GNRC","ITRI","REZI","SHLS","SPWR",
        "CSIQ","JKS","MAXN","RUN","VVNT","ZGAR","AMPE","AMPX",
        "AMPS","AMPY","AMRK","AMRS","AMRX","AMSC","AMSG","AMST",
    ],

    "CONSOMMATION_RETAIL": [
        "CELH","HIMS","PRPL","XPOF","LQDT","BIRD","OLLI","FIVE",
        "BOOT","BJ","CHEF","CHWY","CLOV","COOK","COUR","COVA",
        "CPRI","CPRX","CPRT","CPSI","CPSS","CPTA","CPTK","CPTS",
        "CRAI","CRBU","CRCT","CRDF","CRDL","CREG","CREV","CREX",
        "CRGE","CRHC","CRIS","CRKN","CRMT","CRNC","CRNX","CROX",
        "CRPG","CRSP","CRSR","CRST","CRTD","CRTX","CRUS","CRVL",
        "CRVO","CRVW","CRWS","CRXT","CRZY","CSBR","CSCO","CSCW",
    ],

    "INDUSTRIE_ROBOTIQUE": [
        "IRBT","NVTS","THNK","BRBS","BRTX","BTCS","BTCY","BTDG",
        "BTEK","BTEL","BTEM","BTEN","BTEQ","BTER","BTES","BTET",
        "BTEX","BTEY","BTEZ","BTFX","BTGC","BTHM","BTIM","BTIO",
        "BTLG","BTMD","BTOS","BTOW","BTRA","BTRW","BTTX","BTTZ",
        "BTUR","BTUS","BTVI","BTWN","BTWO","BTXC","BTYG","BUBU",
        "BUCK","BURL","BUSE","BVFL","BWAC","BWAY","BWCM","BWEN",
        "BWFG","BWMN","BWXT","BXMT","BXRX","BXSL","BXSX","BYFC",
    ],
}

# Watchlist prioritaire — toujours surveillée
WATCHLIST_CORE = [
    "NVDA","AMD","CRDO","CELH","RKLB","ASTS","IONQ","DDOG",
    "NET","PLTR","HIMS","SOFI","AFRM","GTLB","RXRX","BEAM",
    "TMDX","SOUN","BBAI","ENVX","AEHR","WOLF","CFLT","DOCN",
]

def get_all_tickers() -> list:
    """Retourne tous les tickers de l'univers."""
    seen = set()
    result = []
    for tickers in UNIVERSE.values():
        for t in tickers:
            if t not in seen:
                seen.add(t)
                result.append(t)
    return result

def get_tickers_by_sector(sector: str) -> list:
    return UNIVERSE.get(sector, [])

ALL_TICKERS = get_all_tickers()
TOTAL_TICKERS = len(ALL_TICKERS)
