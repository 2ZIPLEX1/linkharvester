; Minimal GDI+ library for AutoHotkey v2
; Adapted from Gdip_All.ahk by tic (Tariq Porter)

; Function: Gdip_Startup
; Description: Initializes GDI+
Gdip_Startup() {
    if !DllCall("GetModuleHandle", "str", "gdiplus", "UPtr")
        DllCall("LoadLibrary", "str", "gdiplus")
    
    si := Buffer(24, 0)                     ; sizeof(GdiplusStartupInput) = 24
    NumPut("UInt", 1, si, 0)                ; GdiplusVersion = 1
    
    gdipToken := 0
    DllCall("gdiplus\GdiplusStartup", "UPtr*", &gdipToken, "UPtr", si.Ptr, "UPtr", 0)
    return gdipToken
}

; Function: Gdip_Shutdown
; Description: Closes GDI+
Gdip_Shutdown(gdipToken) {
    DllCall("gdiplus\GdiplusShutdown", "UPtr", gdipToken)
    if hModule := DllCall("GetModuleHandle", "str", "gdiplus", "UPtr")
        DllCall("FreeLibrary", "UPtr", hModule)
    return 0
}

; Function: Gdip_CreateBitmap
; Description: Creates a new bitmap
Gdip_CreateBitmap(width, height, format := 0x26200A) {  ; Format = PixelFormat32bppARGB
    pBitmap := 0
    DllCall("gdiplus\GdipCreateBitmapFromScan0", "int", width, "int", height, "int", 0, "int", format, "UPtr", 0, "UPtr*", &pBitmap)
    return pBitmap
}

; Function: Gdip_GraphicsFromImage
; Description: Creates a graphics object from an image
Gdip_GraphicsFromImage(pBitmap) {
    pGraphics := 0
    DllCall("gdiplus\GdipGetImageGraphicsContext", "UPtr", pBitmap, "UPtr*", &pGraphics)
    return pGraphics
}

; Function: Gdip_DeleteGraphics
; Description: Deletes a graphics object
Gdip_DeleteGraphics(pGraphics) {
    return DllCall("gdiplus\GdipDeleteGraphics", "UPtr", pGraphics)
}

; Function: Gdip_DisposeImage
; Description: Disposes an image
Gdip_DisposeImage(pBitmap) {
    return DllCall("gdiplus\GdipDisposeImage", "UPtr", pBitmap)
}

; Function: Gdip_CopyFromScreen
; Description: Copies from the screen to a graphics context
Gdip_CopyFromScreen(x, y, x2, y2, width, height, pGraphics) {
    return DllCall("gdiplus\GdipDrawImageRectI", "UPtr", pGraphics, "UPtr", GetDesktopHBITMAP(x, y, width, height), "int", x2, "int", y2, "int", width, "int", height)
}

; Function: GetDesktopHBITMAP
; Description: Gets a handle to a bitmap of the desktop
GetDesktopHBITMAP(x, y, w, h) {
    ; Get the desktop DC
    hdc := DllCall("GetDC", "UPtr", 0, "UPtr")
    
    ; Create a compatible DC
    hdcMem := DllCall("CreateCompatibleDC", "UPtr", hdc, "UPtr")
    
    ; Create a compatible bitmap
    hBitmap := DllCall("CreateCompatibleBitmap", "UPtr", hdc, "int", w, "int", h, "UPtr")
    
    ; Select the bitmap into the compatible DC
    hOld := DllCall("SelectObject", "UPtr", hdcMem, "UPtr", hBitmap, "UPtr")
    
    ; Copy from the desktop DC to the compatible DC
    DllCall("BitBlt", "UPtr", hdcMem, "int", 0, "int", 0, "int", w, "int", h, "UPtr", hdc, "int", x, "int", y, "uint", 0x00CC0020)  ; SRCCOPY
    
    ; Select the old bitmap back into the compatible DC
    DllCall("SelectObject", "UPtr", hdcMem, "UPtr", hOld, "UPtr")
    
    ; Delete the compatible DC
    DllCall("DeleteDC", "UPtr", hdcMem)
    
    ; Release the desktop DC
    DllCall("ReleaseDC", "UPtr", 0, "UPtr", hdc)
    
    ; Create Bitmap from the HBITMAP
    pBitmap := 0
    DllCall("gdiplus\GdipCreateBitmapFromHBITMAP", "UPtr", hBitmap, "UPtr", 0, "UPtr*", &pBitmap)
    
    ; Delete the HBITMAP
    DllCall("DeleteObject", "UPtr", hBitmap)
    
    return pBitmap
}

; Function: Gdip_SaveBitmapToFile
; Description: Saves a bitmap to a file
Gdip_SaveBitmapToFile(pBitmap, sOutput, quality := 100) {
    ; Get the encoder CLSID for PNG
    CLSID := Buffer(16, 0)
    
    ; PNG encoder
    str := "557CF406-1A04-11D3-9A73-0000F81EF32E"
    CLSIDFromString(str, CLSID)
    
    ; Save the bitmap
    return DllCall("gdiplus\GdipSaveImageToFile", "UPtr", pBitmap, "WStr", sOutput, "UPtr", CLSID.Ptr, "int", quality ? GetEncoderParameters(quality).Ptr : 0)
}

; Function: CLSIDFromString
; Description: Convert a GUID string to CLSID structure
CLSIDFromString(str, &CLSID) {
    VarSetStrCapacity(&str, 38)
    return DllCall("ole32\CLSIDFromString", "WStr", str, "UPtr", CLSID.Ptr)
}

; Function: GetEncoderParameters
; Description: Creates encoder parameters for JPEG quality
GetEncoderParameters(quality) {
    if (quality < 0 || quality > 100)
        quality := 100
    
    ; Create EncoderParameters structure
    ep := Buffer(24, 0)                     ; sizeof(EncoderParameters) = 24
    
    ; Count of EncoderParameter structures
    NumPut("UInt", 1, ep, 0)                
    
    ; CategoryId - Quality
    NumPut("UInt", 1, ep, 8)                ; Type - ValueTypeLong
    NumPut("UInt", 4, ep, 12)               ; Size of value
    NumPut("UInt", &quality, ep, 16)        ; Value pointer
    
    return ep
}

; Function to provide a simple interface for capturing the screen to a file
SaveScreenCapture(filename) {
    ; Initialize GDI+
    token := Gdip_Startup()
    
    ; Get screen dimensions
    width := A_ScreenWidth
    height := A_ScreenHeight
    
    ; Create a bitmap
    pBitmap := Gdip_CreateBitmap(width, height)
    
    ; Get a graphics context
    pGraphics := Gdip_GraphicsFromImage(pBitmap)
    
    ; Copy from screen
    Gdip_CopyFromScreen(0, 0, 0, 0, width, height, pGraphics)
    
    ; Save the bitmap
    Gdip_SaveBitmapToFile(pBitmap, filename)
    
    ; Clean up
    Gdip_DeleteGraphics(pGraphics)
    Gdip_DisposeImage(pBitmap)
    Gdip_Shutdown(token)
    
    return true
}