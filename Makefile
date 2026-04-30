.PHONY: test-wealthfolio-query
test-wealthfolio-query:
	./tests/wealthfolio_query/build_fixture.sh
	./tests/wealthfolio_query/run-all.sh
