import React, { useState, useCallback } from 'react';
import {
  Box,
  Button,
  Card,
  CardContent,
  CardHeader,
  CircularProgress,
  Container,
  Divider,
  Grid,
  List,
  ListItem,
  ListItemIcon,
  ListItemText,
  Paper,
  Typography,
  IconButton,
  Tooltip,
} from '@mui/material';
import { useDropzone } from 'react-dropzone';
import { useSnackbar } from 'notistack';
import CloudUploadIcon from '@mui/icons-material/CloudUpload';
import DescriptionIcon from '@mui/icons-material/Description';
import DeleteIcon from '@mui/icons-material/Delete';
import { documentsAPI } from '../services/api';

function DocumentsPage() {
  const [documents, setDocuments] = useState([]);
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [deletingId, setDeletingId] = useState(null);
  const { enqueueSnackbar } = useSnackbar();

  const fetchDocuments = useCallback(async () => {
    try {
      setLoading(true);
      const response = await documentsAPI.listDocuments();
      setDocuments(response.data.documents || []);
    } catch (error) {
      console.error('Error fetching documents:', error);
      enqueueSnackbar('Failed to load documents', { variant: 'error' });
    } finally {
      setLoading(false);
    }
  }, [enqueueSnackbar]);

  React.useEffect(() => {
    fetchDocuments();
  }, [fetchDocuments]);

  const onDrop = useCallback(
    async (acceptedFiles) => {
      if (acceptedFiles.length === 0) return;

      try {
        setUploading(true);
        await documentsAPI.uploadDocuments(acceptedFiles);
        enqueueSnackbar('Documents uploaded successfully', { variant: 'success' });
        await fetchDocuments();
      } catch (error) {
        console.error('Error uploading documents:', error);
        enqueueSnackbar('Failed to upload documents', { variant: 'error' });
      } finally {
        setUploading(false);
      }
    },
    [enqueueSnackbar, fetchDocuments]
  );

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      'application/pdf': ['.pdf'],
      'text/plain': ['.txt'],
      'application/vnd.openxmlformats-officedocument.wordprocessingml.document': ['.docx'],
    },
    maxSize: 50 * 1024 * 1024, // 50MB
    multiple: true,
  });

  const handleDelete = async (documentId) => {
    if (!window.confirm('Are you sure you want to delete this document?')) return;
    
    try {
      setDeletingId(documentId);
      // Replace with actual delete API call
      // await documentsAPI.deleteDocument(documentId);
      enqueueSnackbar('Document deleted successfully', { variant: 'success' });
      await fetchDocuments();
    } catch (error) {
      console.error('Error deleting document:', error);
      enqueueSnackbar('Failed to delete document', { variant: 'error' });
    } finally {
      setDeletingId(null);
    }
  };

  return (
    <Container maxWidth="lg" sx={{ mt: 4, mb: 4 }}>
      <Grid container spacing={3}>
        <Grid item xs={12}>
          <Card>
            <CardHeader title="Upload Documents" />
            <Divider />
            <CardContent>
              <Paper
                variant="outlined"
                {...getRootProps()}
                sx={{
                  p: 4,
                  border: '2px dashed',
                  borderColor: 'divider',
                  backgroundColor: isDragActive ? 'action.hover' : 'background.paper',
                  textAlign: 'center',
                  cursor: 'pointer',
                  '&:hover': {
                    borderColor: 'primary.main',
                    backgroundColor: 'action.hover',
                  },
                }}
              >
                <input {...getInputProps()} />
                <CloudUploadIcon sx={{ fontSize: 48, color: 'text.secondary', mb: 2 }} />
                <Typography variant="h6" gutterBottom>
                  {isDragActive ? 'Drop the files here' : 'Drag & drop files here, or click to select files'}
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  Supported formats: PDF, TXT, DOCX (Max 50MB)
                </Typography>
                {uploading && (
                  <Box sx={{ mt: 2 }}>
                    <CircularProgress size={24} />
                    <Typography variant="body2" sx={{ mt: 1 }}>
                      Uploading files...
                    </Typography>
                  </Box>
                )}
              </Paper>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12}>
          <Card>
            <CardHeader title="My Documents" />
            <Divider />
            <CardContent>
              {loading ? (
                <Box display="flex" justifyContent="center" p={4}>
                  <CircularProgress />
                </Box>
              ) : documents.length === 0 ? (
                <Box textAlign="center" p={4}>
                  <Typography variant="body1" color="text.secondary">
                    No documents uploaded yet. Upload some files to get started.
                  </Typography>
                </Box>
              ) : (
                <List>
                  {documents.map((doc, index) => (
                    <React.Fragment key={doc.id || index}>
                      <ListItem
                        secondaryAction={
                          <Tooltip title="Delete document">
                            <IconButton
                              edge="end"
                              aria-label="delete"
                              onClick={() => handleDelete(doc.id || index)}
                              disabled={deletingId === (doc.id || index)}
                            >
                              {deletingId === (doc.id || index) ? (
                                <CircularProgress size={24} />
                              ) : (
                                <DeleteIcon />
                              )}
                            </IconButton>
                          </Tooltip>
                        }
                      >
                        <ListItemIcon>
                          <DescriptionIcon />
                        </ListItemIcon>
                        <ListItemText
                          primary={doc.name || `Document ${index + 1}`}
                          secondary={`Uploaded on ${new Date().toLocaleDateString()}`}
                        />
                      </ListItem>
                      {index < documents.length - 1 && <Divider component="li" />}
                    </React.Fragment>
                  ))}
                </List>
              )}
            </CardContent>
          </Card>
        </Grid>
      </Grid>
    </Container>
  );
}

export default DocumentsPage;
