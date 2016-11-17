all: translations

translations:
	pylupdate5 $$(find barvocuc -name '*.py' -o -name '*.ui') \
		-ts barvocuc/translations/*.ts
	for f in barvocuc/translations/*.ts; do \
		lrelease-qt5 $$f -qm $${f%.ts}.qm; \
	done
