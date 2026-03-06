from fastapi import FastAPI, UploadFile, Form, HTTPException, File
import io
from cams_parser import extract_transactions_from_pdf
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="CAMS CAS Parser API", description="Parse mutual fund CAS PDFs")

# Add CORS middleware so the Next.js frontend can communicate with this API
# (Useful if calling from client side, though you'll likely call from Next.js server side)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # For local development, allow any origin
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def read_root():
    return {"status": "online", "message": "CAMS Parser API is running"}


@app.post("/parse-pdf")
async def parse_pdf(file: UploadFile = File(...), password: str = Form("")):
    """
    Endpoint to receive a PDF file upload and parse it entirely in memory.
    """
    if not file.filename.endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported")

    try:
        # Read the uploaded file entirely into a byte stream in memory
        pdf_bytes = await file.read()
        pdf_stream = io.BytesIO(pdf_bytes)

        # Call the parser and pass the in-memory byte stream instead of a path
        data, msg, unmatched_isins = extract_transactions_from_pdf(pdf_stream, password)

        if data:
            return {
                "status": "success",
                "message": f"Successfully extracted {len(data)} transactions",
                "filename": file.filename,
                "unmatched_isins": unmatched_isins,
                "transactions": data,
            }
        else:
            raise HTTPException(status_code=400, detail=msg)

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Server error during processing: {str(e)}"
        )
