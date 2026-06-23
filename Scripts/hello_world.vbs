On Error Resume Next

MsgBox "HELLO_FROM_VBS"

If Err.Number <> 0 Then
    WScript.Echo "VBS_MSGBOX_ERROR: " & Err.Description
    Err.Clear
End If

If IsObject(CLMainForm) Then
    CLMainForm.WriteLog "HELLO_FROM_VBS via CLMainForm.WriteLog"
    If Err.Number <> 0 Then
        WScript.Echo "VBS_CLMAINFORM_ERROR: " & Err.Description
        Err.Clear
    End If
Else
    WScript.Echo "NO_CLMAINFORM"
End If
