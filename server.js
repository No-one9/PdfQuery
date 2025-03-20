// server.js
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
    destination: 'data/',
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

app.post("/ask",async(req,res)=>{
    const{query}=req.body
    if(!query){
        return res.status(400).json({error:"Query text is required"})
    }
    try{
        const response=await axios.post(FLASK_API_URL,{query});
        res.json(response.data)
    }
    catch(error){
        console.error("Error calling Flask API:", error.message);
        res.status(500).json({
            error: "Internal server error",
            details:error.response?.data || error.message
        });
    }
});

app.listen(PORT,()=>{
    console.log(`Node.js server running on http://localhost:${PORT}`)
})