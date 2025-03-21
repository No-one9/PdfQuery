const { spawn } = require('child_process');
const express= require("express");
const axios=require('axios');
const path=require('path')
const fs=require('fs')
const app= express();
const PORT =3000;
const multer = require('multer'); 
const FLASK_API_URL="http://127.0.0.1:8000/query"

const storage = multer.diskStorage({
    destination: 'Data/',
    filename: (req, file, cb) => {
        const sanitizedName = path.basename(file.originalname);
        cb(null, sanitizedName);
    }
});

const upload = multer({
    storage: storage,
    limits: { fileSize: 10 * 1024 * 1024 }, // 10MB limit
    fileFilter: (req, file, cb) => {
        if (path.extname(file.originalname).toLowerCase() === '.pdf') {
            cb(null, true);
        } else {
            cb(new Error('Only PDF files are allowed'));
        }
    }
});

// Handle PDF uploads
app.post('/upload', upload.single('pdf'), (req, res) => {
    if (!req.file) {
        return res.status(400).json({ success: false, error: 'No file uploaded' });
    }

    // Rebuild vector store with error handling
    const pythonProcess = spawn('python3', ['create_database.py']);
    
    pythonProcess.stderr.on('data', (data) => {
        console.error(`Python error: ${data}`);
    });

    pythonProcess.on('close', (code) => {
        if (code === 0) {
            res.json({ 
                success: true,
                filename: req.file.filename
            });
        } else {
            res.status(500).json({
                success: false,
                error: 'Failed to process PDF'
            });
        }
    });
});
app.use(express.json());

app.use(express.static(path.join(__dirname,'public')));

app.post("/ask", async (req, res) => {
    const { query } = req.body;
    
    if (!query || typeof query !== 'string') {
        return res.status(400).json({ 
            error: "Valid query text is required" 
        });
    }

    try {
        const pythonProcess = spawn('python3', ['query_data.py', query]);
        let responseData = '';
        let errorData = '';

        pythonProcess.stdout.on('data', (data) => {
            responseData += data.toString();
        });

        pythonProcess.stderr.on('data', (data) => {
            errorData += data.toString();
        });

        pythonProcess.on('close', (code) => {
            if (code !== 0) {
                console.error('Query error:', errorData);
                return res.status(500).json({
                    error: "Query processing failed",
                    details: errorData
                });
            }

            try {
                const result = JSON.parse(responseData);
                res.json(result);
            } catch (parseError) {
                console.error('Response parse error:', parseError);
                res.status(500).json({
                    error: "Invalid response format",
                    details: responseData
                });
            }
        });

    } catch (error) {
        console.error("Server error:", error);
        res.status(500).json({
            error: "Internal server error",
            details: error.message
        });
    }
});
app.listen(PORT,()=>{
    console.log(`Node.js server running on http://localhost:${PORT}`)
})