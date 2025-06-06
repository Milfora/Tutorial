let pdfDoc = null;
let scale = 1.0;
let markups = [];
let currentTool = null;
let drawing = false;
let currentPoints = [];

function loadProjectData() {
    fetch(`/projects/${window.projectId}/data`).then(r => r.json()).then(data => {
        markups = data.markups ? JSON.parse(data.markups) : [];
        scale = data.scale || 1.0;
        renderMarkups();
    });
    fetch(`/projects/${window.projectId}/pdf`).then(resp => resp.blob()).then(blob => {
        if(blob.size>0) {
            const fileURL = URL.createObjectURL(blob);
            loadPdf(fileURL);
        }
    });
}

function loadPdf(url) {
    const loadingTask = pdfjsLib.getDocument(url);
    loadingTask.promise.then(function(pdf) {
        pdfDoc = pdf;
        pdf.getPage(1).then(function(page) {
            const viewport = page.getViewport({ scale: 1.5 });
            const canvas = document.getElementById('pdf-canvas');
            const context = canvas.getContext('2d');
            canvas.height = viewport.height;
            canvas.width = viewport.width;
            const renderContext = {
                canvasContext: context,
                viewport: viewport
            };
            page.render(renderContext).promise.then(function() {
                const drawCanvas = document.getElementById('draw-canvas');
                drawCanvas.width = canvas.width;
                drawCanvas.height = canvas.height;
                renderMarkups();
            });
        });
    });
}

function renderMarkups() {
    const canvas = document.getElementById('draw-canvas');
    const ctx = canvas.getContext('2d');
    ctx.clearRect(0,0,canvas.width,canvas.height);
    ctx.strokeStyle = 'red';
    ctx.fillStyle = 'rgba(255,0,0,0.3)';
    markups.forEach(m => {
        if(m.type==='polygon' || m.type==='cloud') {
            ctx.beginPath();
            m.points.forEach((p,i)=>{ i===0?ctx.moveTo(p[0],p[1]):ctx.lineTo(p[0],p[1]); });
            ctx.closePath();
            ctx.stroke();
            if(m.type==='polygon') ctx.fill();
        } else if(m.type==='polyline') {
            ctx.beginPath();
            m.points.forEach((p,i)=>{ i===0?ctx.moveTo(p[0],p[1]):ctx.lineTo(p[0],p[1]); });
            ctx.stroke();
        } else if(m.type==='point') {
            ctx.beginPath();
            ctx.arc(m.points[0][0], m.points[0][1], 5, 0, 2*Math.PI);
            ctx.fill();
        }
    });
}

function canvasClick(e) {
    if(!currentTool) return;
    const rect = e.target.getBoundingClientRect();
    const x = e.clientX - rect.left;
    const y = e.clientY - rect.top;
    if(!drawing) {
        drawing = true;
        currentPoints = [[x,y]];
    } else {
        currentPoints.push([x,y]);
        if(currentTool==='point') {
            finishShape();
        }
    }
}

function canvasDblClick() {
    if(drawing && (currentTool==='polygon' || currentTool==='polyline' || currentTool==='cloud')) {
        finishShape();
    }
}

function finishShape() {
    markups.push({type: currentTool, points: currentPoints});
    drawing = false;
    currentPoints = [];
    renderMarkups();
}

function setTool(t) {
    currentTool = t;
}

function setScale() {
    const val = prompt('Enter scale: real units per pixel', scale);
    if(val) scale = parseFloat(val);
}

function saveProject() {
    document.getElementById('markups-input').value = JSON.stringify(markups);
    document.getElementById('scale-input').value = scale;
    const pdfUpload = document.getElementById('pdf-upload');
    if(pdfUpload.files.length>0) {
        document.getElementById('pdf-file-input').files = pdfUpload.files;
    }
    document.getElementById('save-form').submit();
}

document.addEventListener('DOMContentLoaded', function() {
    const canvas = document.getElementById('draw-canvas');
    if(canvas) {
        canvas.addEventListener('click', canvasClick);
        canvas.addEventListener('dblclick', canvasDblClick);
        document.getElementById('poly-btn').addEventListener('click', ()=>setTool('polygon'));
        document.getElementById('line-btn').addEventListener('click', ()=>setTool('polyline'));
        document.getElementById('point-btn').addEventListener('click', ()=>setTool('point'));
        document.getElementById('cloud-btn').addEventListener('click', ()=>setTool('cloud'));
        document.getElementById('scale-btn').addEventListener('click', setScale);
        document.getElementById('save-btn').addEventListener('click', saveProject);
        document.getElementById('pdf-upload').addEventListener('change', e=>{
            const file = e.target.files[0];
            if(file) {
                const url = URL.createObjectURL(file);
                loadPdf(url);
            }
        });
        loadProjectData();
    }
});
