# Honda-Acura-ECM-Checksum-fix

# Universal Honda/Keihin Checksum Fixer

A lightweight Python tool designed to verify and fix checksums for Honda/Acura ECU ROMs (Keihin SH70xx/SH72xx). It features automatic algorithm detection and a fallback "Drift Compensation" mode for unknown or non-standard checksums.

## Features

* **Auto-Detection:** Automatically scans the original ROM to identify standard 8-bit, 16-bit, and 32-bit checksum algorithms (Sum-Zero and Stored-Sum).
* **Smart Drift Compensation:** If a standard checksum cannot be found (common in newer gen ECUs with complex tables), the tool calculates the mathematical "drift" caused by your patches and balances the file's total sum by modifying the padding.
* **Dual Injection Modes:** In Drift Mode, offers automatic detection for:
    * **Safe Mode:** Modifies the very end of the file (safest, lowest risk of corruption).
    * **Compat Mode:** Modifies the empty space immediately following the code block (useful if the ECU ignores the end of the file).
* **Universal Compatibility:** Works with `.bin` files from standard tuning suites (RomRaider, TunerPro, etc.).

## Usage

1.  **Install Python:** Ensure Python 3.x is installed on your system.
2.  **Place Files:** Put the script (`checksum_fix.py`) in the same folder as your Original and Patched `.bin` files.
3.  **Run:** Double-click the script or run via command line:
    ```bash
    python checksum_fix.py
    ```
4.  **Follow Prompts:** Enter the filenames when asked.

## How "Drift Mode" Works

Modern Keihin ECUs often use checksums that are difficult to locate without expensive commercial tools. However, almost all of them rely on an additive verification method (where the sum of the memory must equal a specific value).

**Drift Compensation** relies on a mathematical principle:
> If `Sum(Original) == Target` and `Sum(Patched) == Target + Drift`, we can restore validity by subtracting `Drift` from an empty area of the file (0xFF padding).

This forces `Sum(Patched)` to equal `Sum(Original)` exactly, satisfying the ECU's check without needing to modify the actual checksum bytes or digital signatures.

### Modes Explained

When Drift Mode is active, you will see two options:

* **[1] Safe Mode (Recommended):**
    * **Location:** 0x2FFFFC (End of File).
    * **Why:** This is the safest method. It modifies the last 4 bytes of the 3MB/4MB file.
    * **Use Case:** Always try this first. It works on 95% of ECUs that scan the entire memory block.

* **[2] Compat Mode:**
    * **Location:** Auto-detected (e.g., 0x165440).
    * **Why:** Some ECUs stop reading memory immediately after the code ends and ignore the empty space at the end of the file. If you use "Safe Mode" and the car cranks but does not start, the ECU is likely ignoring the fix at the end of the file.
    * **Use Case:** Use this ONLY if Option 1 results in a no-start condition. It places the fix immediately after the valid data ends.

## Requirements

* Python 3.6+
* No external libraries required (uses standard `struct`, `os`, `sys`).

## License

This project is licensed under the **GNU General Public License v3.0**. 
You are free to use, modify, and distribute this software, but all modifications must remain open-source.
