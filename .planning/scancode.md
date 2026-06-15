after codebase scanning, spawn additional codebase mapper subagents for the additional tasks of read-only analysis, output each report into timestamped file in .planning/code_analysis. do not fix yet, I will start new debug session or urgent phase insertion or quick task for the fix.
A. do a read-only trace of the function and data flow in the code, to generate the full flowchart of each funtion call before a success gromacs export.
B. for all the codes in this repo, critically scan the code and trace the logic of different options to identift vunlability, suspecious code, or issues leading to safety concerns or performance lost. do not run anything.
pay specific attention to any nested for-loops, unit mismatch and atom number mismatch, and any bugs you can identify.
C. For the documentation, cross-check for consistency with the code, and suggest possible citation to add. We now have cli and gui, check carefully, you better spawn multple agents for this documentationa check
D. identify the necessary lib to be packaged into a portable distribution and suggest how to change the pyinstaller script in scripts to reduce bundled size
