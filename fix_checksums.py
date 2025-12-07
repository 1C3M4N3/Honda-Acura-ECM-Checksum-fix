import os
import struct
import sys
#Author: The Iceman

# --- Helper Functions ---
def getFile(filename):
    """Finds file in current directory, handling quotes."""
    cwd = os.getcwd()
    path = os.path.join(cwd, filename)
    if os.path.exists(path): return path
    cleanName = filename.strip('"').strip("'")
    path = os.path.join(cwd, cleanName)
    if os.path.exists(path): return path
    return None

def calculateSum32(data):
    """Calculates 32-bit Big Endian sum of data."""
    if len(data) % 4 != 0:
        data += b'\xFF' * (4 - (len(data) % 4))
    count = len(data) // 4
    words = struct.unpack(f'>{count}I', data)
    return sum(words)

# --- Algorithm 1: Standard Detection ---

def detectStandardAlgo(data):
    """
    Scans for standard Keihin checksums (Sum-Zero or Stored).
    Returns info dict if found, or None.
    """
    print("[-] Scanning for standard Checksum algorithms...")
    
    realEnd = len(data)
    while realEnd > 0 and data[realEnd-1] == 0xFF:
        realEnd -= 1
    realEnd = (realEnd + 3) & ~3 # Align to 4
    
    skipOffsets = [0, 0x4000, 0x8000, 0x10000, 0x20000]

    for startAddr in skipOffsets:
        if startAddr >= realEnd: continue
        
        scanRegion = data[startAddr:realEnd]
        regionSum = calculateSum32(scanRegion)
        mask = 0xFFFFFFFF

        for i in range(len(scanRegion) - 4, len(scanRegion) - 64, -4):
            valInFile = int.from_bytes(scanRegion[i:i+4], 'big')
            
            if (regionSum & mask) == 0:
                return { 'type': 'zero', 'offset': startAddr + i, 'start': startAddr, 'end': realEnd }
            
            if (regionSum & mask) == ((valInFile * 2) & mask):
                return { 'type': 'stored', 'offset': startAddr + i, 'start': startAddr, 'end': realEnd }
    return None

# --- Algorithm 2: Smart Drift Fix ---

def findInjectionPoints(data):
    """
    Finds two potential spots for the blind fix:
    1. EOF (End of File) - The very last bytes of the file.
    2. EOD (End of Data) - The first empty bytes immediately after the code.
    """
    fileSize = len(data)
    
    # 1. Find Safe Spot (EOF)
    safePoint = fileSize - 4
    if int.from_bytes(data[safePoint:safePoint+4], 'big') != 0xFFFFFFFF:
        # If last bytes aren't empty, scan back
        for i in range(fileSize - 4, 0, -4):
             if int.from_bytes(data[i:i+4], 'big') == 0xFFFFFFFF:
                 safePoint = i
                 break
    
    # 2. Find Compat Spot (End of actual data)
    # Scan backwards until we hit non-FF data
    idx = fileSize - 1
    while idx > 0 and data[idx] == 0xFF:
        idx -= 1
    # The first free byte is idx + 1. Align to 4.
    dataEnd = (idx + 1)
    while dataEnd % 4 != 0: dataEnd += 1
    
    return safePoint, dataEnd

def applyDriftFix(origPath, patchPath, patchData):
    print("\n[!] Standard Checksum not detected.")
    print("    -> Engaging SMART DRIFT COMPENSATION Mode.")
    
    with open(origPath, 'rb') as f: origData = f.read()

    # 1. Calculate Diff
    sumOrig = calculateSum32(origData)
    sumPatch = calculateSum32(patchData)
    diff = sumPatch - sumOrig
    
    print(f"    Original Sum: {sumOrig}")
    print(f"    Patched Sum:  {sumPatch}")
    
    if diff == 0:
        print("    [*] Sums already match. No fix needed.")
        return patchData

    # 2. Detect Points
    safePoint, dataPoint = findInjectionPoints(patchData)
    
    print("\n    [?] Select Injection Method:")
    print(f"        [1] Safe Mode (Recommended) - Fix at End of File (0x{safePoint:X})")
    print(f"        [2] Compat Mode - Fix immediately after Data (0x{dataPoint:X})")
    print(f"            * Use [2] ONLY if car cranks but doesn't start with [1].")
    print(f"        [3] Manual Address")
    
    choice = input("    Select [1], [2], or [3]: ").strip()
    
    fixOffset = safePoint # Default
    
    if choice == '2':
        fixOffset = dataPoint
    elif choice == '3':
        while True:
            try:
                val = input("    Enter Hex Address: ").strip().replace("0x","")
                fixOffset = int(val, 16)
                break
            except:
                print("Invalid Hex.")

    print(f"    [-] Applying fix at: 0x{fixOffset:X}")
    
    currentVal = int.from_bytes(patchData[fixOffset:fixOffset+4], 'big')
    if currentVal != 0xFFFFFFFF and currentVal != 0:
        print(f"    [WARNING] Target address 0x{fixOffset:X} is NOT empty (0x{currentVal:X}). Overwriting anyway...")
        
    newVal = (currentVal - diff) & 0xFFFFFFFF
    print(f"    Old Value: 0x{currentVal:X}")
    print(f"    New Value: 0x{newVal:X}")
    
    patchData[fixOffset:fixOffset+4] = newVal.to_bytes(4, 'big')
    
    # 4. Verify
    verifySum = calculateSum32(patchData)
    if verifySum == sumOrig:
        print("    [+] Verification: SUCCESS (Sums Match)")
    else:
        print(f"    [!] Verification: FAILED (Target: {sumOrig}, Got: {verifySum})")
        
    return patchData

# --- Main ---

def main():
    print("--- Universal Honda/Keihin Checksum Fixer ---")
    
    origName = input("Original ROM: ").strip()
    patchName = input("Patched ROM:  ").strip()
    
    origPath = getFile(origName)
    patchPath = getFile(patchName)
    
    if not origPath or not patchPath:
        print("Error: Files not found.")
        input("Press Enter...")
        return

    with open(origPath, 'rb') as f: origData = f.read()
    with open(patchPath, 'rb') as f: patchData = bytearray(f.read())

    # 1. Try Standard Algo
    algoInfo = detectStandardAlgo(origData)
    
    if algoInfo:
        print(f"\n[+] Standard Algorithm Found: {algoInfo['type'].upper()}")
        print(f"    Location: 0x{algoInfo['offset']:X}")
        
        start, end, offset = algoInfo['start'], algoInfo['end'], algoInfo['offset']
        regionData = patchData[start:end]
        currentTotal = calculateSum32(regionData)
        currentVal = int.from_bytes(patchData[offset:offset+4], 'big')
        
        mask = 0xFFFFFFFF
        if algoInfo['type'] == 'zero':
            newVal = (-(currentTotal - currentVal)) & mask
        else: 
            newVal = (currentTotal - currentVal) & mask
            
        patchData[offset:offset+4] = newVal.to_bytes(4, 'big')
        print(f"    Fixed Checksum: 0x{newVal:X}")
        
    else:
        # 2. Fallback to Smart Drift Fix
        patchData = applyDriftFix(origPath, patchPath, patchData)

    # 3. Save
    outName = f"{os.path.splitext(patchName)[0]}_fixed.bin"
    with open(outName, 'wb') as f:
        f.write(patchData)
        
    print(f"\n[SUCCESS] File saved: {outName}")
    if sys.stdout.isatty():
        input("Press Enter to close...")

if __name__ == "__main__":
    main()