// server.js
const express= require("express");
const axios=require('axios');
const path=require('path')
const app= express();
const PORT =3000;
const FLASK_API_URL="http://127.0.0.1:8000/query"
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