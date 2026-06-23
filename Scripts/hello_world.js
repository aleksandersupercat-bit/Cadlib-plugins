try {
    var shell = new ActiveXObject("WScript.Shell");
    shell.Popup("HELLO_FROM_JS", 0, "JScript test", 64);
} catch (e) {
}

try {
    if (typeof(CLMainForm) !== "undefined" && CLMainForm != null) {
        CLMainForm.WriteLog("HELLO_FROM_JS via CLMainForm.WriteLog");
    }
} catch (e2) {
}
