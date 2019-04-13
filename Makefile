GIT_HASH=$(shell git rev-parse --short HEAD)
GIT_ROOT=$(shell git rev-parse --show-toplevel)
PUBLISHERS=akileos dargaud delcourt dupuis glenat laboiteabulles
PUBLISHERS_SELECTED=$(if $(publisher),$(publisher),$(PUBLISHERS))

# scrape all publishers.
# To scrape a single publisher: use make scrape publisher=$publisher,
# e.g: make scrape publisher=delcourt
.PHONY: scrape
scrape:
	@for p in $(PUBLISHERS_SELECTED) ; do \
		$(MAKE) --no-print-directory _scrape publisher=$${p}; \
	done

.PHONY: _scrape
_scrape:
	@cd backend; ./scrape.sh $(publisher)
