import _ from 'lodash';
import axios from 'axios';

export default class HttpClient {
    constructor(defaultOptions = {}) {
        this._defaultOptions = defaultOptions;
    }
    _getOptions(options) {
        return _.merge(options, this._defaultOptions);
    }
    get(url, options = {}) {
        return axios.get(url, this._getOptions(options));
    }
    post(url, data, options = {}) {
        return axios.post(url, data, this._getOptions(options));
    }
    put(url, data, options = {}) {
        return axios.put(url, data, this._getOptions(options) );
    }
    patch(url, data, options = {}) {
        return axios.patch(url, data, this._getOptions(options));
    }
    delete(url, options = {}) {
        return axios.delete(url, this._getOptions(options));
    }
}
