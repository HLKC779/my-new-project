import axios from 'axios';

// Create axios instance with base URL
const api = axios.create({
  baseURL: 'http://localhost:8000', // Update this with your backend URL
  headers: {
    'Content-Type': 'application/json',
  },
});

// Add a request interceptor to include auth token
api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Auth API
export const authAPI = {
  login: (email, password) => {
    const formData = new FormData();
    formData.append('username', email);
    formData.append('password', password);
    
    return api.post('/api/v1/auth/login', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
  },
  
  register: (userData) => api.post('/api/v1/auth/register', userData),
  
  getMe: () => api.get('/api/v1/auth/me'),
};

// Documents API
export const documentsAPI = {
  uploadDocuments: (files) => {
    const formData = new FormData();
    files.forEach((file) => {
      formData.append('files', file);
    });
    
    return api.post('/api/v1/rag/upload', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
  },
  
  listDocuments: () => api.get('/api/v1/rag/documents'),
  
  query: (question) => api.post('/api/v1/rag/query', { question }),
};

// Users API
export const usersAPI = {
  getProfile: () => api.get('/api/v1/users/me'),
  updateProfile: (userData) => api.put('/api/v1/users/me', userData),
};

export default api;
