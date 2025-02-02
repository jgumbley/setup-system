download: venv
	. venv/bin/activate && \
	python download.py -u jimgumbley -p 73

venv:
	python3 -m venv venv
	. venv/bin/activate && \
	pip install -r requirements.txt

clean:
	rm -rf venv

clean_img:
	rm -f *.jpg
