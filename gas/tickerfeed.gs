/**
 * tickerfeed: GOOGLEFINANCE-like custom function backed by the tickerfeed API.
 *
 * Script properties (Extensions → Apps Script → Project settings → Script properties):
 *   TICKERFEED_URL      e.g. http://1.2.3.4:8742
 *   TICKERFEED_API_KEY  same as api_key in server .env
 */

var ATTRIBUTES = ['price', 'currency', 'name'];
var CLIENT_CACHE_SECONDS = 5 * 60;
var CACHE_PREFIX = 'tickerfeed:';
var NA = '#N/A';

/**
 * Returns a quote attribute, like GOOGLEFINANCE.
 *
 * @param {string|Array<Array<string>>} symbols "LSE:VUSA", "NYSE:KO" or a range of them.
 * @param {string} attribute price (default), currency, name.
 * @param {boolean} gbp convert pence-quoted LSE instruments to GBP, default FALSE.
 * @return attribute value(s), same shape as symbols.
 * @customfunction
 */
function TICKERFEED(symbols, attribute, gbp) {
    attribute = (attribute || 'price').toString().toLowerCase();
    if (ATTRIBUTES.indexOf(attribute) === -1) {
        throw new Error('unknown attribute ' + attribute + ', expected one of ' + ATTRIBUTES.join(', '));
    }
    gbp = gbp === true;

    if (!Array.isArray(symbols)) {
        var query = symbols.toString().trim();
        if (!query) {
            return '';
        }
        return resultValue_(fetchResults_([query], gbp)[query], attribute);
    }

    var queries = [];
    symbols.forEach(function (row) {
        row.forEach(function (cell) {
            var query = cell.toString().trim();
            if (query && queries.indexOf(query) === -1) {
                queries.push(query);
            }
        });
    });
    var results = fetchResults_(queries, gbp);

    return symbols.map(function (row) {
        return row.map(function (cell) {
            var query = cell.toString().trim();
            if (!query) {
                return '';
            }
            return resultValue_(results[query], attribute);
        });
    });
}

/** Like GOOGLEFINANCE: unknown symbol or provider failure → #N/A, the reason goes to the execution log. */
function resultValue_(result, attribute) {
    if (result.error) {
        console.log('%s: %s', result.query, result.error);
        return NA;
    }
    var value = result.quote[attribute];
    if (value === null || value === undefined) {
        return '';
    }
    return value;
}

/** Map query → {quote, error}; serves from CacheService, fetches the rest in one request. */
function fetchResults_(queries, gbp) {
    var cache = CacheService.getScriptCache();
    var keys = queries.map(function (query) {
        return CACHE_PREFIX + (gbp ? 'gbp:' : '') + query;
    });
    var cached = cache.getAll(keys);

    var results = {};
    var missing = [];
    queries.forEach(function (query, i) {
        if (cached[keys[i]]) {
            results[query] = JSON.parse(cached[keys[i]]);
        } else {
            missing.push(query);
        }
    });
    if (!missing.length) {
        return results;
    }

    var props = PropertiesService.getScriptProperties();
    var url = props.getProperty('TICKERFEED_URL') + '/v1/quotes?symbols=' + encodeURIComponent(missing.join(',')) + '&gbp=' + gbp;
    var response = UrlFetchApp.fetch(url, {
        headers: {'X-Api-Key': props.getProperty('TICKERFEED_API_KEY')},
        muteHttpExceptions: true,
    });
    if (response.getResponseCode() !== 200) {
        throw new Error('tickerfeed responded ' + response.getResponseCode() + ': ' + response.getContentText().slice(0, 200));
    }

    var toCache = {};
    JSON.parse(response.getContentText()).results.forEach(function (result) {
        results[result.query] = result;
        // ошибки провайдера и stale не кешируем — пусть следующий пересчёт попробует снова
        if (result.quote && !result.stale) {
            toCache[CACHE_PREFIX + (gbp ? 'gbp:' : '') + result.query] = JSON.stringify(result);
        }
    });
    cache.putAll(toCache, CLIENT_CACHE_SECONDS);
    return results;
}
