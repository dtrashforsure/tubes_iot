MAIN := DECO_buku_iot_cerdas

.PHONY: pdf clean check

pdf:
	latexmk -pdf -interaction=nonstopmode -synctex=1 $(MAIN).tex

clean:
	latexmk -C $(MAIN).tex

check:
	chktex -q -n 1 -n 8 -n 13 -n 24 $(MAIN).tex
