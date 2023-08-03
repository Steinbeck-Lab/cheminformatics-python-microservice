import selfies as sf

from fastapi import APIRouter, Query, status, HTTPException
from fastapi.responses import Response
from rdkit import Chem
from typing import Literal, Dict
from STOUT import translate_forward, translate_reverse
from app.modules.toolkits.cdk_wrapper import (
    getCDKSDGMol,
    getCXSMILES,
    getCanonSMILES,
    getInChI,
)
from app.modules.toolkits.rdkit_wrapper import (
    get3Dconformers,
    get2Dmol,
    getRDKitCXSMILES,
)
from app.modules.toolkits.openbabel_wrapper import (
    getOBMol,
    getOBCanonicalSMILES,
    getOBInChI,
)
from app.schemas import HealthCheck
from app.schemas.pydanticmodels import ErrorResponse

router = APIRouter(
    prefix="/convert",
    tags=["convert"],
    dependencies=[],
    responses={404: {"description": "Not found"}},
)


@router.get("/", include_in_schema=False)
@router.get(
    "/health",
    tags=["healthcheck"],
    summary="Perform a Health Check on Converters Module",
    response_description="Return HTTP Status Code 200 (OK)",
    status_code=status.HTTP_200_OK,
    response_model=HealthCheck,
    include_in_schema=False,
)
def get_health() -> HealthCheck:
    """
    ## Perform a Health Check
    Endpoint to perform a healthcheck on. This endpoint can primarily be used Docker
    to ensure a robust container orchestration and management is in place. Other
    services which rely on proper functioning of the API service will not deploy if this
    endpoint returns any other HTTP status code except 200 (OK).
    Returns:
        HealthCheck: Returns a JSON response with the health status
    """
    return HealthCheck(status="OK")


@router.get(
    "/mol2D",
    summary="Generates 2D Coordinates for the input molecules",
    responses={400: {"model": ErrorResponse}},
)
async def Create2D_Coordinates(
    smiles: str = Query(
        title="SMILES",
        description="SMILES representation of the molecule",
        examples=[
            "CCO",
            "C=O",
        ],
    ),
    toolkit: Literal["cdk", "rdkit", "openbabel"] = Query(
        default="cdk", description="Cheminformatics toolkit used in the backend"
    ),
):
    """
    Generates 2D Coordinates using the CDK Structure diagram generator/RDKit/Open Babel and returns the mol block.

    Parameters:
    - **SMILES**: required (str): The SMILES string.
    - **toolkit** (str, optional): The toolkit to use for generating 2D coordinates.
        - Supported values: "cdk" (default), "rdkit", "openbabel".

    Returns:
    - molblock (str): The generated mol block with 2D coordinates as a plain text response.

    Raises:
    - ValueError: If the SMILES string is not provided or is invalid.
    """
    try:
        if toolkit == "cdk":
            return Response(
                content=getCDKSDGMol(smiles).replace("$$$$\n", ""),
                media_type="text/plain",
            )
        elif toolkit == "rdkit":
            return Response(
                content=get2Dmol(smiles),
                media_type="text/plain",
            )
        else:
            mol = Chem.MolFromSmiles(smiles)
            if mol:
                return Response(
                    content=getOBMol(smiles),
                    media_type="text/plain",
                )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get(
    "/mol3D",
    summary="Generates 3D Coordinates for the input molecules",
    responses={400: {"model": ErrorResponse}},
)
async def Create3D_Coordinates(
    smiles: str = Query(
        title="SMILES",
        description="SMILES representation of the molecule",
        examples=[
            "CCO",
            "C=O",
        ],
    ),
    toolkit: Literal["rdkit", "openbabel"] = Query(
        default="rdkit", description="Cheminformatics toolkit used in the backend"
    ),
):
    """
    Generates a random 3D conformer from SMILES using the specified molecule toolkit.

    Parameters:
    - **SMILES**: required (str): The SMILES representation of the molecule.
    - **toolkit**: optional (str): The molecule toolkit to use.
        - Supported values: "rdkit" (default) & "openbabel".


    Returns:
    - molblock (str): The generated mol block with 3D coordinates as a plain text response.

    Raises:
    - ValueError: If the SMILES string is not provided or is invalid.
    """

    try:
        if toolkit == "rdkit":
            return Response(
                content=get3Dconformers(smiles, depict=False),
                media_type="text/plain",
            )
        elif toolkit == "openbabel":
            mol = Chem.MolFromSmiles(smiles)
            if mol:
                return Response(
                    content=getOBMol(smiles, threeD=True),
                    media_type="text/plain",
                )

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get(
    "/smiles",
    response_model=str,
    summary="Generate SMILES from a given input",
    responses={400: {"model": ErrorResponse}},
)
async def IUPACname_or_SELFIES_to_SMILES(
    input_text: str = Query(
        title="Input IUPAC name or SELFIES",
        description="IUPAC name or SELFIES representation of the molecule",
        examples=[
            "benzene",
            "[C][C][C]",
        ],
    ),
    representation: Literal["iupac", "selfies"] = Query(
        default="iupac", description="Required type of format convertion"
    ),
):
    """
    Generate SMILES from a given IUPAC name or a SELFIES representation.

    Parameters:
    - **input_text**: required (str): The input text containing either the IUPAC name or SELFIES representation.
    - **representation**: optional (str): The representation type of the input text.
        - Supported values: "iupac" (default) & "selfies".

    Returns:
    - If representation is "iupac": The generated SMILES string corresponding to the given IUPAC name.
    - If representation is "selfies": The generated SMILES string corresponding to the given SELFIES representation.

    Notes:
    - The IUPAC name should follow the standard IUPAC naming conventions for organic compounds.
    - SELFIES (Self-Referencing Embedded Strings) is a concise yet expressive chemical string notation.

    Example Usage:
    - To generate SMILES from an IUPAC name: /smiles?input_text=benzene&representation=iupac
    - To generate SMILES from a SELFIES representation: /smiles?input_text=[C][C][C]&representation=selfies
    """
    try:
        if representation == "iupac":
            iupac_name = translate_reverse(input_text)
            if iupac_name:
                return str(iupac_name)
        elif representation == "selfies":
            selfies_out = sf.decoder(input_text)
            if selfies_out:
                return str(selfies_out)
        else:
            raise HTTPException(
                status_code=400,
                detail="Error reading input text, please check again.",
            )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get(
    "/canonicalsmiles",
    response_model=str,
    summary="Generate CanonicalSMILES from a given SMILES",
    responses={400: {"model": ErrorResponse}},
)
async def SMILES_Canonicalise(
    smiles: str = Query(
        title="SMILES",
        description="SMILES representation of the molecule",
        examples=[
            "CCO",
            "C=O",
        ],
    ),
    toolkit: Literal["cdk", "rdkit", "openbabel"] = Query(
        default="cdk", description="Cheminformatics toolkit used in the backend"
    ),
):
    """
    Canonicalizes a given SMILES string according to the allowed toolkits.

    Parameters:
    - **SMILES**: required (str): The input SMILES string to be canonicalized.
    - **toolkit**: optional (str): The toolkit to use for canonicalization.
        - Supported values: "cdk" (default), "rdkit" & "openbabel".

    Returns:
    - SMILES (str): The canonicalized SMILES string.

    Raises:
    - ValueError: If the SMILES string is empty or contains invalid characters.
    - ValueError: If an unsupported toolkit option is provided.

    """
    try:
        if toolkit == "cdk":
            return str(getCanonSMILES(smiles))
        elif toolkit == "rdkit":
            mol = Chem.MolFromSmiles(smiles)
            if mol:
                return str(Chem.MolToSmiles(mol, kekuleSmiles=True))
            else:
                raise HTTPException(
                    status_code=400,
                    detail="Error reading input text, please check again.",
                )
        elif toolkit == "openbabel":
            return str(getOBCanonicalSMILES(smiles))
        else:
            raise HTTPException(
                status_code=400,
                detail="Error reading input text, please check again.",
            )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get(
    "/cxsmiles",
    response_model=str,
    summary="Generate CXSMILES from a given SMILES",
    responses={400: {"model": ErrorResponse}},
)
async def SMILES_to_CXSMILES(
    smiles: str = Query(
        title="SMILES",
        description="SMILES representation of the molecule",
        examples=[
            "CCO",
            "C=O",
        ],
    ),
    toolkit: Literal["cdk", "rdkit"] = Query(
        default="cdk", description="Cheminformatics toolkit used in the backend"
    ),
):
    """
    Convert SMILES to CXSMILES. For more informations:
    - https://docs.chemaxon.com/display/docs/chemaxon-extended-smiles-and-smarts-cxsmiles-and-cxsmarts.md

    Parameters:
    - **SMILES**: required (str): The input SMILES string to convert.
    - **toolkit**: optional (str): The toolkit to use for conversion.
        - Supported values: "cdk" (default) & "rdkit".

    Returns:
    - CXSMILES (str): The converted CXSMILES string.

    Raises:
    - ValueError: If the SMILES string is empty or contains invalid characters.
    - ValueError: If an unsupported toolkit option is provided.

    Note:
    - CXSMILES is a Chemaxon Extended SMILES which is used for storing special features of the molecules after the SMILES string.
    """
    try:
        if toolkit == "cdk":
            cxsmiles = getCXSMILES(smiles)
            if cxsmiles:
                return str(cxsmiles)
        else:
            cxsmiles = getRDKitCXSMILES(smiles)
            if cxsmiles:
                return str(cxsmiles)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get(
    "/inchi",
    response_model=str,
    summary="Generate InChI from a given SMILES",
    responses={400: {"model": ErrorResponse}},
)
async def SMILES_to_InChI(
    smiles: str = Query(
        title="SMILES",
        description="SMILES representation of the molecule",
        examples=[
            "CCO",
            "C=O",
        ],
    ),
    toolkit: Literal["cdk", "rdkit", "openbabel"] = Query(
        default="cdk", description="Cheminformatics toolkit used in the backend"
    ),
):
    """
    Convert SMILES to InChI.

    Parameters:
    - **SMILES**: required (str): The input SMILES string to convert.
    - **toolkit**: optional (str): The toolkit to use for conversion.
        - Supported values: "cdk" (default), "openbabel" & "rdkit".

    Returns:
    - InChI (str): The resulting InChI string.

    Raises:
    - ValueError: If the SMILES string is empty or contains invalid characters.
    - ValueError: If an unsupported toolkit option is provided.

    """
    try:
        if toolkit == "cdk":
            inchi = getInChI(smiles)
            if inchi:
                return str(inchi)
        elif toolkit == "rdkit":
            mol = Chem.MolFromSmiles(smiles)
            if mol:
                inchi = Chem.inchi.MolToInchi(mol)
                if inchi:
                    return str(inchi)
        elif toolkit == "openbabel":
            inchi = getOBInChI(smiles)
            if inchi:
                return str(inchi)
        else:
            raise HTTPException(
                status_code=400,
                detail="Error reading input text, please check again.",
            )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get(
    "/inchikey",
    response_model=str,
    summary="Generate InChI-Key from a given SMILES",
    responses={400: {"model": ErrorResponse}},
)
async def SMILES_to_InChIKey(
    smiles: str = Query(
        title="SMILES",
        description="SMILES representation of the molecule",
        examples=[
            "CCO",
            "C=O",
        ],
    ),
    toolkit: Literal["cdk", "rdkit", "openbabel"] = Query(
        default="cdk", description="Cheminformatics toolkit used in the backend"
    ),
):
    """
    Convert SMILES to InChI-Key.

    Parameters:
    - **SMILES**: required (str): The input SMILES string to convert.
    - **toolkit**: optional (str): The toolkit to use for conversion.
        - Supported values: "cdk" (default), "openbabel" & "rdkit".

    Returns:
    - InChI-Key (str): The resulting InChI-Key string.

    Raises:
    - ValueError: If the SMILES string is empty or contains invalid characters.
    - ValueError: If an unsupported toolkit option is provided.

    """
    try:
        if toolkit == "cdk":
            inchikey = getInChI(smiles, InChIKey=True)
            if inchikey:
                return str(inchikey)

        elif toolkit == "rdkit":
            mol = Chem.MolFromSmiles(smiles)
            if mol:
                inchikey = Chem.inchi.MolToInchiKey(mol)
                if inchikey:
                    return str(inchikey)
        elif toolkit == "openbabel":
            inchikey = getOBInChI(smiles, InChIKey=True)
            if inchikey:
                return str(inchikey)
        else:
            raise HTTPException(
                status_code=400,
                detail="Error reading input text, please check again.",
            )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get(
    "/iupac",
    response_model=str,
    summary="Generates IUPAC name using STOUT package",
    responses={400: {"model": ErrorResponse}},
)
async def SMILES_to_IUPACname(
    smiles: str = Query(
        title="SMILES",
        description="SMILES representation of the molecule",
        examples=[
            "CCO",
            "C=O",
        ],
    ),
):
    """
    Generates IUPAC name using STOUT package. For more information:
    - Rajan, K., Zielesny, A. & Steinbeck, C. STOUT: SMILES to IUPAC names using neural machine translation. J Cheminform 13, 34 (2021). https://doi.org/10.1186/s13321-021-00512-4

    Parameters:
    - **SMILES**: required (str): The input SMILES string to convert.

    Returns:
    - IUPAC name (str): The resulting IUPAC name of the chemical compound.

    Raises:
    - ValueError: If the SMILES string is empty or contains invalid characters.

    Note:
    - Here we are using STOUT v2.0 which is available at: https://github.com/Kohulan/Smiles-TO-iUpac-Translator

    Disclaimer:
    - Since STOUT is a deep learning model it does halucinate or may provide incorrect IUPAC names at times.

    """
    try:
        iupac = translate_forward(smiles)
        if iupac:
            return str(iupac)
        else:
            raise HTTPException(
                status_code=400,
                detail="Error reading input text, please check again.",
            )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get(
    "/selfies",
    response_model=str,
    summary="Generates SELFIES string for a given SMILES string",
    responses={400: {"model": ErrorResponse}},
)
async def encode_SELFIES(
    smiles: str = Query(
        title="SMILES",
        description="SMILES representation of the molecule",
        examples=[
            "CCO",
            "C=O",
        ],
    ),
):
    """
    Generates SELFIES string for a given SMILES string. For more information:
    - Krenn et al, SELFIES and the future of molecular string representations, Patterns, https://doi.org/10.1016/j.patter.2022.100588.

    Parameters:
    - **SMILES**: required (str): The input SMILES string to convert.

    Returns:
    - SELFIES (str): The resulting SELFIES of the chemical compound.

    Raises:
    - ValueError: If the SMILES string is empty or contains invalid characters.
    """
    try:
        selfies_e = sf.encoder(smiles)
        if selfies_e:
            return str(selfies_e)
        else:
            raise HTTPException(
                status_code=400,
                detail="Error reading input text, please check again.",
            )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get(
    "/formats",
    response_model=Dict,
    summary="Convert SMILES to various molecular formats using different toolkits",
    responses={400: {"model": ErrorResponse}},
)
async def SMILES_convert_to_Formats(
    smiles: str = Query(
        title="SMILES",
        description="SMILES representation of the molecule",
        examples=[
            "CCO",
            "C=O",
        ],
    ),
    toolkit: Literal["cdk", "rdkit", "openbabel"] = Query(
        default="cdk", description="Cheminformatics toolkit used in the backend"
    ),
):
    """
    Convert SMILES to various molecular formats using different toolkits.

    Parameters:
    - **SMILES**: required (str): The input SMILES string to convert.
    - **toolkit**: optional (str): The toolkit to use for conversion.
        - Supported values: "cdk" (default), "openbabel" & "rdkit".

    Returns:
    - dict: A dictionary containing the converted data in various formats. The dictionary has the following keys:
        - "mol" (str): The generated 2D mol block of the molecule.
        - "canonicalsmiles" (str): The canonical SMILES representation of the molecule.
        - "inchi" (str): The InChI representation of the molecule.
        - "inchikey" (str): The InChIKey representation of the molecule.

    Note:
        - The returned dictionary may contain empty strings if conversion fails or the input SMILES string is invalid.

    Raises:
    - ValueError: If the SMILES string is empty or contains invalid characters.
    - ValueError: If an unsupported toolkit option is provided.
    """
    try:
        if toolkit == "cdk":
            response = {}
            response["mol"] = getCDKSDGMol(smiles).replace("$$$$\n", "")
            response["canonicalsmiles"] = str(getCanonSMILES(smiles))
            response["inchi"] = str(getInChI(smiles))
            response["inchikey"] = str(getInChI(smiles, InChIKey=True))
            return response

        elif toolkit == "rdkit":
            mol = Chem.MolFromSmiles(smiles)
            if mol:
                response = {}
                response["mol"] = Chem.MolToMolBlock(mol)
                response["canonicalsmiles"] = Chem.MolToSmiles(mol, kekuleSmiles=True)
                response["inchi"] = Chem.inchi.MolToInchi(mol)
                response["inchikey"] = Chem.inchi.MolToInchiKey(mol)
                return response
        elif toolkit == "openbabel":
            response = {}
            response["mol"] = getOBMol(smiles)
            response["canonicalsmiles"] = getOBCanonicalSMILES(smiles)
            response["inchi"] = getOBInChI(smiles)
            response["inchikey"] = getOBInChI(smiles, InChIKey=True)
            return response
        else:
            raise HTTPException(
                status_code=400,
                detail="Error reading SMILES string, please check again.",
            )
    except Exception as e:
        raise HTTPException(
            status_code=400, detail="Error processing request: " + str(e)
        )
