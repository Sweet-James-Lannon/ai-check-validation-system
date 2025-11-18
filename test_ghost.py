import sys
import locale
import ghostscript

args = [
    "ps2pdf", # actual value doesn't matter
    "-dNOPAUSE", "-dBATCH", "-dSAFER",
    "-sDEVICE=pdfwrite",
    "-sOutputFile=" + sys.argv[1],
    "-f",  sys.argv[2]
    ]
ghostscript.Ghostscript(*args)