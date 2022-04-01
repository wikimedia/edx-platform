// import axios from 'axios';
import _ from 'lodash';

export default class HttpClient {
    constructor(defaultOptions = {}) {
        this._defaultOptions = defaultOptions;
    }
    _getOptions(options) {
        return _.merge(options, this._defaultOptions);
    }
    get(url, options = {}) {
        return fetch(url, { method: "GET", ...this._getOptions(options) });
    }
    post(url, data, options = {}) {
        return fetch(url, data, this._getOptions(options));
    }
    put(url, data, options = {}) {
        return fetch(url, data, this._getOptions(options));
    }
    patch(url, data, options = {}) {
        return fetch(url, data, this._getOptions(options));
    }
    delete(url, options = {}) {
        return fetch(url, this._getOptions(options));
    }
}
