from rdkit import Chem
from rdkit.Chem import rdDepictor
from rdkit.Chem.Draw import rdMolDraw2D
from app.modules.cdkmodules import getCDKSDG
import xml.etree.ElementTree as ET
from jpype import JClass


def getCDKDepiction(smiles: str, molSize=(512, 512)):
    """This function takes the user input SMILES and Depicts it
       using the CDK Depiction Generator.
    Args:
            smiles (string): SMILES string given by the user.
    Returns:
            imag (PIL): CDK Structure Depiction as a pillow image.
            image (png): CDK Structure Depiction as a PNG image.
    """
    cdk_base = "org.openscience.cdk"
    StandardGenerator = JClass(
        cdk_base + ".renderer.generators.standard.StandardGenerator"
    )
    DepictionGenerator = JClass(cdk_base + ".depict.DepictionGenerator")()
    Color = JClass("java.awt.Color")
    UniColor = JClass(cdk_base + ".renderer.color.UniColor")

    # Generate depiction with settings
    DepictionGenerator.withSize(molSize[0], molSize[1]).withAtomValues().withParam(
        StandardGenerator.StrokeRatio.class_, 1.0
    ).withAnnotationColor(Color.BLACK).withParam(
        StandardGenerator.AtomColor.class_, UniColor(Color.BLACK)
    ).withBackgroundColor(
        Color.WHITE
    ).withZoom(
        2.0
    )
    getString = JClass("java.lang.String")
    moleculeSDG = getCDKSDG(smiles)

    # Rotate molecule
    point = JClass(cdk_base + ".geometry.GeometryTools").get2DCenter(moleculeSDG)
    JClass(cdk_base + ".geometry.GeometryTools").rotate(
        moleculeSDG, point, (rotate * JClass("java.lang.Math").PI / 180.0)
    )

    mol_image = DepictionGenerator.depict(moleculeSDG)
    mol_imagex = mol_image.toSvgStr(getString("px")).getBytes()

    # Fix scaling
    mol_root = ET.fromstring(mol_imagex)
    new_width = molSize[0]
    new_height = molSize[1]
    mol_root.set("width", "{}px".format(new_width))
    mol_root.set("height", "{}px".format(new_height))

    # Write the modified SVG element to a string
    rescaled_mol = ET.tostring(mol_root, encoding="unicode")

    return rescaled_mol


def getRDKitDepiction(smiles, molSize=(512, 512), kekulize=True):
    """This function takes the user input SMILES and Canonicalize it
       using the RDKit.
    Args:
            smiles (string): SMILES string given by the user.
    Returns:
            imag (PIL): CDK Structure Depiction as a pillow image.
            image (png): CDK Structure Depiction as a PNG image.
    """
    mol = Chem.MolFromSmiles(smiles)
    mc = Chem.Mol(mol.ToBinary())
    if kekulize:
        try:
            Chem.Kekulize(mc)
        except:
            mc = Chem.Mol(mol.ToBinary())
    if not mc.GetNumConformers():
        rdDepictor.Compute2DCoords(mc)
    drawer = rdMolDraw2D.MolDraw2DSVG(molSize[0], molSize[1])
    drawer.DrawMolecule(mc)
    drawer.FinishDrawing()
    svg = drawer.GetDrawingText()
    return svg.replace("svg:", "")
