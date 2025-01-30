const { app, BrowserWindow } = require("electron");
const { exec } = require("child_process");
const path = require("path");

let mainWindow;
let flaskProcess;

function createWindow() {
    mainWindow = new BrowserWindow({
        width: 1024,
        height: 768,
        webPreferences: {
            nodeIntegration: true,
        },
    });

    mainWindow.loadURL("http://127.0.0.1:5000");

    mainWindow.on("closed", function () {
        mainWindow = null;
    });
}

app.whenReady().then(() => {
    const pythonPath = path.join(__dirname, "python.exe");
    const flaskScript = path.join(__dirname, "app.py");

    console.log("Запуск Flask-приложения...");

    flaskProcess = exec(`"${pythonPath}" "${flaskScript}"`, { cwd: __dirname }, (error, stdout, stderr) => {
        if (error) {
            console.error(`Ошибка запуска Flask: ${error.message}`);
            return;
        }
        if (stderr) {
            console.error(`Stderr: ${stderr}`);
        }
        console.log(`Stdout: ${stdout}`);
    });

    createWindow();

    app.on("activate", function () {
        if (BrowserWindow.getAllWindows().length === 0) createWindow();
    });
});

app.on("window-all-closed", function () {
    if (process.platform !== "darwin") {
        app.quit();
    }
});

app.on("quit", function () {
    if (flaskProcess) {
        flaskProcess.kill();
        console.log("Flask-приложение завершено.");
    }
});
