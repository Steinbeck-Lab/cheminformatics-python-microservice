from fastapi import Body, Request, APIRouter
from typing import Optional
from typing_extensions import Annotated
from rdkit import Chem
from rdkit.Chem.EnumerateStereoisomers import (
    EnumerateStereoisomers,
)
from chembl_structure_pipeline import standardizer, checker
from fastapi.responses import Response, HTMLResponse
from app.modules.npscorer import getNPScore
from app.modules.classyfire import classify, result
from app.modules.cdkmodules import getCDKSDGMol, getTanimotoSimilarityCDK
from app.modules.depict import getRDKitDepiction, getCDKDepiction
from app.modules.rdkitmodules import get3Dconformers, getTanimotoSimilarityRDKit
from app.modules.coconutdescriptors import getCOCONUTDescriptors
from app.modules.alldescriptors import getTanimotoSimilarity
import pandas as pd
from fastapi.templating import Jinja2Templates

router = APIRouter(
    prefix="/chem",
    tags=["chem"],
    dependencies=[],
    responses={404: {"description": "Not found"}},
)

templates = Jinja2Templates(directory="app/templates")


@router.get("/")
async def chem_index():
    return {"module": "chem", "message": "Successful", "status": 200}


@router.get("/stereoisomers")
async def SMILES_to_Stereo_Isomers(smiles: str):
    """
    Enumerate all possible stereoisomers based on the chiral centres in the given SMILES:

    - **SMILES**: required (query parameter)
    """
    if any(char.isspace() for char in smiles):
        smiles = smiles.replace(" ", "+")
    mol = Chem.MolFromSmiles(smiles)
    if mol:
        isomers = tuple(EnumerateStereoisomers(mol))
        smilesArray = []
        for smi in sorted(Chem.MolToSmiles(x, isomericSmiles=True) for x in isomers):
            smilesArray.append(smi)
        return smilesArray
    else:
        return "Error reading SMILES string, check again."


@router.post("/standardize")
async def Standardize_Mol(mol: Annotated[str, Body(embed=True)]):
    """
    Standardize molblock using the ChEMBL curation pipeline routine
    and return the Standardized molecule, SMILES, InChI and InCHI-Key:

    - **mol**: required
    """
    if mol:
        standardized_mol = standardizer.standardize_molblock(mol)
        rdkit_mol = Chem.MolFromMolBlock(standardized_mol)
        smiles = Chem.MolToSmiles(rdkit_mol, kekuleSmiles=True)
        response = {}
        response["standardized_mol"] = standardized_mol
        response["cannonical_smiles"] = smiles
        response["inchi"] = Chem.inchi.MolToInchi(rdkit_mol)
        response["inchikey"] = Chem.inchi.MolToInchiKey(rdkit_mol)
        return response
    else:
        return "Error reading SMILES string, check again."


@router.get("/descriptors")
async def SMILES_Descriptors(
    smiles: str, format: Optional[str] = "json", toolkit: Optional[str] = "rdkit"
):
    """
    Generate standard descriptors for the input molecules (SMILES):

    - **SMILES**: required (query)
    """
    if smiles:
        if format == "html":
            data = getCOCONUTDescriptors(smiles, toolkit)
            if toolkit == "all":
                headers = ["Descriptor name", "RDKit Descriptors", "CDK Descriptors"]
                df = pd.DataFrame.from_dict(
                    data, orient="index", columns=headers[1:], dtype=object
                )
                df.insert(0, headers[0], df.index)
            else:
                headers = ["Descriptor name", "Values"]
                df = pd.DataFrame.from_dict(data, orient="index", columns=headers[1:])
                df.insert(0, headers[0], df.index)
            with open("app/templates/style.css", "r") as file:
                css_style = file.read()
            html_table = df.to_html(index=False)
            return Response(content=css_style + html_table, media_type="text/html")
        else:
            return getCOCONUTDescriptors(smiles, toolkit)


@router.get("/npscore")
async def NPlikeliness_Score(smiles: str):
    """
    Generate natural product likeliness score based on RDKit implementation

    - **SMILES**: required (query)
    """
    if smiles:
        np_score = getNPScore(smiles)
        return np_score


@router.get("/classyfire/classify")
async def ClassyFire_Classify(smiles: str):
    """
    Generate ClassyFire-based classifications using SMILES as input.

    - **SMILES**: required (query)
    """
    if smiles:
        data = await classify(smiles)
        return data


@router.get("/classyfire/{id}/result")
async def ClassyFire_result(id: str):
    """
    Get the ClassyFire classification results using ID.

    - **ID**: required (query)
    """
    if id:
        data = await result(id)
        return data


@router.get("/cdk2d")
async def CDK2D_Coordinates(smiles: str):
    """
    Generate 2D Coordinates using the CDK Structure diagram generator and return the mol block.

    - **SMILES**: required (query)
    """
    if smiles:
        mol = Chem.MolFromSmiles(smiles)
        if mol:
            return Response(
                content=getCDKSDGMol(smiles).replace("$$$$\n", ""),
                media_type="text/plain",
            )
        else:
            return "Error reading SMILES string, check again."


@router.get("/rdkit3d")
async def RDKit3D_Mol(smiles: str):
    """
    Generate 3D Coordinates using RDKit and return the mol block.

    - **SMILES**: required (query)
    """
    if smiles:
        mol = Chem.MolFromSmiles(smiles)
        if mol:
            return Response(
                content=get3Dconformers(smiles).replace("$$$$\n", ""),
                media_type="text/plain",
            )
        else:
            return "Error reading SMILES string, check again."


@router.get("/tanimoto")
async def Tanimoto_Similarity(smiles: str, toolkit: Optional[str] = "cdk"):
    """
    Generate the Tanimoto similarity index for a given pair of SMILES strings.

    - **SMILES**: required (query)
    - **toolkit**: optional (defaults: cdk)
    """
    if len(smiles.split(",")) == 2:
        try:
            smiles1, smiles2 = smiles.split(",")
            if toolkit == "rdkit":
                Tanimoto = getTanimotoSimilarityRDKit(smiles1, smiles2)
            else:
                Tanimoto = getTanimotoSimilarityCDK(smiles1, smiles2)
            return Tanimoto
        except ValueError:
            return 'Please give a SMILES pair with "," separated. (Example: api.naturalproducts.net/chem/tanimoto?smiles=CN1C=NC2=C1C(=O)N(C(=O)N2C)C,CN1C=NC2=C1C(=O)NC(=O)N2C)'
    elif len(smiles.split(",")) > 2:
        try:
            matrix = getTanimotoSimilarity(smiles, toolkit)
            return Response(content=matrix, media_type="text/html")
        except ValueError:
            return 'Please give a SMILES pair with "," separated. (Example: api.naturalproducts.net/chem/tanimoto?smiles=CN1C=NC2=C1C(=O)N(C(=O)N2C)C,CN1C=NC2=C1C(=O)NC(=O)N2C)'
    else:
        return 'Please give a SMILES pair with "," separated. (Example: api.naturalproducts.net/chem/tanimoto?smiles=CN1C=NC2=C1C(=O)N(C(=O)N2C)C,CN1C=NC2=C1C(=O)NC(=O)N2C)'


@router.get("/depict")
async def Depict2D_molecule(
    smiles: str,
    generator: Optional[str] = "cdksdg",
    width: Optional[int] = 512,
    height: Optional[int] = 512,
    rotate: Optional[int] = 0,
    CIP: Optional[bool] = False,
    unicolor: Optional[bool] = False,
):
    """
    Generate 2D Depictions using CDK or RDKit using given parameters.

    - **SMILES**: required (query)
    - **generator**: optional (defaults: cdk)
    - **width**: optional (defaults: 512)
    - **height**: optional (defaults: 512)
    - **rotate**: optional (defaults: 0)
    """
    if generator:
        if generator == "cdksdg":
            return Response(
                content=getCDKDepiction(smiles, [width, height], rotate, CIP, unicolor),
                media_type="image/svg+xml",
            )
        else:
            return Response(
                content=getRDKitDepiction(smiles, [width, height], rotate),
                media_type="image/svg+xml",
            )


@router.get("/checkerrors")
async def Check_Errors(smiles: str, fix: Optional[bool] = False):
    """
    Check issues for a given SMILES string and standardize it using the ChEMBL curation pipeline.

    - **SMILES**: required (query)
    - **fix**: optional (defaults: False)
    """
    if any(char.isspace() for char in smiles):
        smiles = smiles.replace(" ", "+")
    if smiles:
        mol = Chem.MolFromSmiles(smiles, sanitize=False)
        if mol:
            mol_block = Chem.MolToMolBlock(mol)
            if len(checker.check_molblock(mol_block)) == 0:
                return "No Errors Found"
            else:
                issues = checker.check_molblock(mol_block)
                if fix:
                    issues = checker.check_molblock(mol_block)
                    standardized_mol = standardizer.standardize_molblock(mol_block)
                    issues_new = checker.check_molblock(standardized_mol)
                    rdkit_mol = Chem.MolFromMolBlock(standardized_mol)
                    standardizedsmiles = Chem.MolToSmiles(rdkit_mol)
                    if len(issues_new) == 0:
                        issues_new = "No Errors Found"

                    parsed_data = {
                        "source": {
                            "SMILES": smiles,
                            "messages": issues,
                        },
                        "standardized": {
                            "SMILES": standardizedsmiles,
                            "messages": issues_new,
                        },
                    }
                    return parsed_data
                else:
                    return issues
        else:
            return "Error reading SMILES string, check again."
    else:
        return "Error reading SMILES string, check again."


@router.get("/depict3D", response_class=HTMLResponse)
async def Depict3D_Molecule(
    request: Request,
    smiles: str,
):
    """
    Generate 3D Depictions using RDKit.

    - **SMILES**: required (query)
    """
    if smiles:
        content = {"request": request, "molecule": get3Dconformers(smiles)}
        return templates.TemplateResponse("mol.html", content)


# @app.get("/molecules/", response_model=List[schemas.Molecule])
# def read_molecules(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
#     molecules = crud.get_molecules(db, skip=skip, limit=limit)
#     return molecules
