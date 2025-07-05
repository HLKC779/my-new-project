import React, { useState, useEffect } from 'react';
import {
  Box,
  Typography,
  Container,
  Grid,
  Card,
  CardContent,
  CardHeader,
  Divider,
  Button,
  CircularProgress,
} from '@mui/material';
import { useNavigate } from 'react-router-dom';
import { documentsAPI } from '../services/api';

function DashboardPage() {
  const [documents, setDocuments] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const navigate = useNavigate();

  useEffect(() => {
    const fetchDocuments = async () => {
      try {
        setLoading(true);
        const response = await documentsAPI.listDocuments();
        setDocuments(response.data.documents || []);
        setError(null);
      } catch (err) {
        setError('Failed to load documents');
        console.error('Error fetching documents:', err);
      } finally {
        setLoading(false);
      }
    };

    fetchDocuments();
  }, []);

  const handleUploadClick = () => {
    navigate('/documents');
  };

  const handleQueryClick = () => {
    navigate('/query');
  };

  return (
    <Container maxWidth="lg" sx={{ mt: 4, mb: 4 }}>
      <Grid container spacing={3}>
        <Grid item xs={12} md={8} lg={9}>
          <Card sx={{ mb: 3 }}>
            <CardHeader title="Welcome to RAG System" />
            <Divider />
            <CardContent>
              <Typography variant="body1" paragraph>
                This is a Retrieval-Augmented Generation (RAG) system for data engineering and AI research.
                You can upload documents and ask questions based on their content.
              </Typography>
              <Box sx={{ display: 'flex', gap: 2, mt: 3 }}>
                <Button
                  variant="contained"
                  color="primary"
                  onClick={handleUploadClick}
                >
                  Upload Documents
                </Button>
                <Button
                  variant="outlined"
                  color="primary"
                  onClick={handleQueryClick}
                >
                  Ask a Question
                </Button>
              </Box>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} md={4} lg={3}>
          <Card>
            <CardHeader title="Quick Stats" />
            <Divider />
            <CardContent>
              {loading ? (
                <Box display="flex" justifyContent="center" p={2}>
                  <CircularProgress size={24} />
                </Box>
              ) : error ? (
                <Typography color="error">{error}</Typography>
              ) : (
                <Box>
                  <Typography variant="h6" component="div" gutterBottom>
                    Documents: {documents.length}
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    Uploaded to the system
                  </Typography>
                </Box>
              )}
            </CardContent>
          </Card>
        </Grid>
      </Grid>
    </Container>
  );
}

export default DashboardPage;
