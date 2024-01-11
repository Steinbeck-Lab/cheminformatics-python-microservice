from __future__ import annotations

from pydantic import BaseModel


class ExtractChemicalInfoResponse(BaseModel):
    """
    A Pydantic model representing a successful response.

    Attributes:
        message (str): A message indicating the success status (default: "Success").
        reference (str): Reference string to the image input.
        smiles (str): SMILES string generated by DECIMER.

    """

    message: str = "Success"
    reference: str
    smiles: str
