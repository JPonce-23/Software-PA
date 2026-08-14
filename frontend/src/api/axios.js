import axios from 'axios';

const api = axios.create({
  baseURL: '/api',
  withCredentials: true,
  headers: {
    'Content-Type': 'application/json',
  },
});

api.interceptors.request.use(
  (config) => {
    if (config.data instanceof FormData) {
      if (typeof config.headers?.delete === 'function') {
        config.headers.delete('Content-Type');
      } else if (config.headers) {
        delete config.headers['Content-Type'];
      }
    } else if (config.data instanceof URLSearchParams) {
      if (typeof config.headers?.set === 'function') {
        config.headers.set('Content-Type', 'application/x-www-form-urlencoded');
      } else {
        config.headers = {
          ...(config.headers || {}),
          'Content-Type': 'application/x-www-form-urlencoded',
        };
      }
    } else if (typeof config.headers?.set === 'function') {
      config.headers.set('Content-Type', 'application/json');
    } else {
      config.headers = {
        ...(config.headers || {}),
        'Content-Type': 'application/json',
      };
    }

    const method = (config.method || 'get').toLowerCase();
    if (['post', 'put', 'patch', 'delete'].includes(method)) {
      const cookies = Object.fromEntries(
        document.cookie
          .split(';')
          .map((item) => item.trim().split('='))
          .filter(([name]) => name)
      );
      const csrfToken = cookies['__Host-pa_csrf'] || cookies.pa_csrf_dev;
      if (csrfToken) {
        config.headers['X-CSRF-Token'] = decodeURIComponent(csrfToken);
      }
    }
    return config;
  },
  (error) => Promise.reject(error)
);

api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response && error.response.status === 401) {
      if (window.location.pathname !== '/login') {
        window.location.href = '/login';
      }
    }
    return Promise.reject(error);
  }
);

export default api;
