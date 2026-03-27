# Dependency

This is only done after the release of quickice v1

# quickice v2 requirements

Create lightweight, standalone, cross-platform executable GUI application of quickice (windows and linux 64 bit first)

The GUI features an all-in-one interface with the following:
1. an interactive phase diagram, that the user can click on the diagram to check
2. textbox to input options
3. info window of info of that point in phase diagram with necessary citation 
4. button to generate 3D structure of the selected point in the phase diagram
5. progress bar to show the generation progress
6. 3D viewer of the generated structures, show one at a time to save resource. simple view of stick/ball and stick and dashed lines of hydrogen bonds
7. option to save the plot/3D structure/export data/image of 3D scene to file

Notes:
a. Cap the number of water molecules for the generation to e.g. 216.
b. Provide minimal explanation to each option (one `i` or `?` next to everything for the user to check, in addition to markdown user manual. Human will provide the pdf manual with screenshot based on the markdown manual)
c. Check the license of the libraries used by genice and suggest whether is ok to just include the licence or we have to change the quickice licence.
