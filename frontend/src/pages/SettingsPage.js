import React, { useState, useEffect } from 'react';
import {
  Avatar,
  Box,
  Button,
  Card,
  CardContent,
  CardHeader,
  CircularProgress,
  Container,
  Divider,
  Grid,
  IconButton,
  List,
  ListItem,
  ListItemIcon,
  ListItemText,
  MenuItem,
  Paper,
  Tab,
  Tabs,
  TextField,
  Typography,
  useTheme,
  Alert,
  Snackbar,
  Switch,
  FormControlLabel,
  FormGroup,
  FormControl,
  InputLabel,
  Select,
  FormHelperText,
} from '@mui/material';
import { useAuth } from '../contexts/AuthContext';
import { usersAPI } from '../services/api';
import { useSnackbar } from 'notistack';
import PersonIcon from '@mui/icons-material/Person';
import EmailIcon from '@mui/icons-material/Email';
import LockIcon from '@mui/icons-material/Lock';
import DeleteIcon from '@mui/icons-material/Delete';
import CloudUploadIcon from '@mui/icons-material/CloudUpload';
import { styled } from '@mui/material/styles';

const StyledAvatar = styled(Avatar)(({ theme }) => ({
  width: 100,
  height: 100,
  margin: '0 auto',
  cursor: 'pointer',
  '&:hover': {
    opacity: 0.8,
  },
}));

const Input = styled('input')({
  display: 'none',
});

function TabPanel(props) {
  const { children, value, index, ...other } = props;

  return (
    <div
      role="tabpanel"
      hidden={value !== index}
      id={`settings-tabpanel-${index}`}
      aria-labelledby={`settings-tab-${index}`}
      {...other}
    >
      {value === index && <Box sx={{ p: 3 }}>{children}</Box>}
    </div>
  );
}

function a11yProps(index) {
  return {
    id: `settings-tab-${index}`,
    'aria-controls': `settings-tabpanel-${index}`,
  };
}

function SettingsPage() {
  const { user: currentUser, updateUser } = useAuth();
  const [tabValue, setTabValue] = useState(0);
  const [profileForm, setProfileForm] = useState({
    full_name: '',
    email: '',
  });
  const [passwordForm, setPasswordForm] = useState({
    currentPassword: '',
    newPassword: '',
    confirmPassword: '',
  });
  const [preferences, setPreferences] = useState({
    darkMode: false,
    notifications: true,
    language: 'en',
  });
  const [loading, setLoading] = useState({
    profile: false,
    password: false,
    preferences: false,
  });
  const [errors, setErrors] = useState({});
  const [avatar, setAvatar] = useState(null);
  const [avatarPreview, setAvatarPreview] = useState('');
  const { enqueueSnackbar } = useSnackbar();
  const theme = useTheme();

  useEffect(() => {
    if (currentUser) {
      setProfileForm({
        full_name: currentUser.full_name || '',
        email: currentUser.email || '',
      });
      // Set avatar preview if user has an avatar
      if (currentUser.avatar_url) {
        setAvatarPreview(currentUser.avatar_url);
      }
    }
  }, [currentUser]);

  const handleTabChange = (event, newValue) => {
    setTabValue(newValue);
  };

  const handleProfileChange = (e) => {
    const { name, value } = e.target;
    setProfileForm({
      ...profileForm,
      [name]: value,
    });
  };

  const handlePasswordChange = (e) => {
    const { name, value } = e.target;
    setPasswordForm({
      ...passwordForm,
      [name]: value,
    });
  };

  const handlePreferenceChange = (e) => {
    const { name, checked, value } = e.target;
    setPreferences({
      ...preferences,
      [name]: name === 'language' ? value : checked,
    });
  };

  const handleAvatarChange = (e) => {
    const file = e.target.files[0];
    if (file) {
      if (file.size > 2 * 1024 * 1024) { // 2MB limit
        enqueueSnackbar('File size should be less than 2MB', { variant: 'error' });
        return;
      }
      setAvatar(file);
      setAvatarPreview(URL.createObjectURL(file));
    }
  };

  const validateProfile = () => {
    const newErrors = {};
    if (!profileForm.full_name.trim()) newErrors.full_name = 'Full name is required';
    if (!profileForm.email.trim()) {
      newErrors.email = 'Email is required';
    } else if (!/\S+@\S+\.\S+/.test(profileForm.email)) {
      newErrors.email = 'Email is invalid';
    }
    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const validatePassword = () => {
    const newErrors = {};
    if (!passwordForm.currentPassword) newErrors.currentPassword = 'Current password is required';
    if (!passwordForm.newPassword) {
      newErrors.newPassword = 'New password is required';
    } else if (passwordForm.newPassword.length < 8) {
      newErrors.newPassword = 'Password must be at least 8 characters';
    }
    if (passwordForm.newPassword !== passwordForm.confirmPassword) {
      newErrors.confirmPassword = 'Passwords do not match';
    }
    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleProfileSubmit = async (e) => {
    e.preventDefault();
    if (!validateProfile()) return;

    try {
      setLoading({ ...loading, profile: true });
      
      // In a real app, you would upload the avatar and update the profile
      // const formData = new FormData();
      // if (avatar) {
      //   formData.append('avatar', avatar);
      // }
      // formData.append('full_name', profileForm.full_name);
      // formData.append('email', profileForm.email);
      // 
      // const response = await usersAPI.updateProfile(formData);
      // updateUser(response.data);
      
      // For demo purposes, just update the local state
      updateUser({
        ...currentUser,
        full_name: profileForm.full_name,
        email: profileForm.email,
        avatar_url: avatarPreview,
      });
      
      enqueueSnackbar('Profile updated successfully', { variant: 'success' });
    } catch (error) {
      console.error('Error updating profile:', error);
      enqueueSnackbar('Failed to update profile', { variant: 'error' });
    } finally {
      setLoading({ ...loading, profile: false });
    }
  };

  const handlePasswordSubmit = async (e) => {
    e.preventDefault();
    if (!validatePassword()) return;

    try {
      setLoading({ ...loading, password: true });
      
      // In a real app, you would send this to your backend
      // await usersAPI.changePassword({
      //   current_password: passwordForm.currentPassword,
      //   new_password: passwordForm.newPassword,
      // });
      
      // For demo purposes, just show a success message
      enqueueSnackbar('Password updated successfully', { variant: 'success' });
      setPasswordForm({
        currentPassword: '',
        newPassword: '',
        confirmPassword: '',
      });
    } catch (error) {
      console.error('Error updating password:', error);
      const errorMessage = error.response?.data?.detail || 'Failed to update password';
      enqueueSnackbar(errorMessage, { variant: 'error' });
    } finally {
      setLoading({ ...loading, password: false });
    }
  };

  const handlePreferencesSubmit = async (e) => {
    e.preventDefault();
    
    try {
      setLoading({ ...loading, preferences: true });
      
      // In a real app, you would save these preferences to your backend
      // await usersAPI.updatePreferences(preferences);
      
      // For demo purposes, just show a success message
      enqueueSnackbar('Preferences saved', { variant: 'success' });
      
      // In a real app, you would update the theme based on the preference
      // if (preferences.darkMode !== theme.palette.mode === 'dark') {
      //   // Toggle theme
      // }
      
    } catch (error) {
      console.error('Error saving preferences:', error);
      enqueueSnackbar('Failed to save preferences', { variant: 'error' });
    } finally {
      setLoading({ ...loading, preferences: false });
    }
  };

  const handleDeleteAccount = () => {
    if (window.confirm('Are you sure you want to delete your account? This action cannot be undone.')) {
      // In a real app, you would call an API to delete the account
      // usersAPI.deleteAccount().then(() => {
      //   logout();
      //   navigate('/login');
      // });
      
      enqueueSnackbar('Account deletion is not implemented in this demo', { variant: 'info' });
    }
  };

  return (
    <Container maxWidth="lg" sx={{ mt: 4, mb: 4 }}>
      <Typography variant="h4" gutterBottom>
        Settings
      </Typography>
      
      <Box sx={{ width: '100%' }}>
        <Box sx={{ borderBottom: 1, borderColor: 'divider' }}>
          <Tabs 
            value={tabValue} 
            onChange={handleTabChange} 
            aria-label="settings tabs"
            variant="scrollable"
            scrollButtons="auto"
          >
            <Tab label="Profile" {...a11yProps(0)} />
            <Tab label="Password" {...a11yProps(1)} />
            <Tab label="Preferences" {...a11yProps(2)} />
            <Tab label="Danger Zone" {...a11yProps(3)} sx={{ color: 'error.main' }} />
          </Tabs>
        </Box>
        
        <TabPanel value={tabValue} index={0}>
          <Grid container spacing={3}>
            <Grid item xs={12} md={4}>
              <Card>
                <CardContent sx={{ textAlign: 'center' }}>
                  <label htmlFor="avatar-upload">
                    <Input
                      accept="image/*"
                      id="avatar-upload"
                      type="file"
                      onChange={handleAvatarChange}
                    />
                    <StyledAvatar
                      src={avatarPreview || undefined}
                      alt={profileForm.full_name || 'User'}
                    >
                      {!avatarPreview && <PersonIcon sx={{ fontSize: 50 }} />}
                    </StyledAvatar>
                    <Button
                      component="span"
                      startIcon={<CloudUploadIcon />}
                      sx={{ mt: 2 }}
                    >
                      Upload Photo
                    </Button>
                  </label>
                  <Typography variant="h6" sx={{ mt: 2 }}>
                    {profileForm.full_name || 'User'}
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    {profileForm.email}
                  </Typography>
                </CardContent>
              </Card>
            </Grid>
            <Grid item xs={12} md={8}>
              <Card>
                <CardHeader title="Profile Information" />
                <Divider />
                <CardContent>
                  <Box component="form" onSubmit={handleProfileSubmit}>
                    <Grid container spacing={3}>
                      <Grid item xs={12}>
                        <TextField
                          fullWidth
                          label="Full Name"
                          name="full_name"
                          value={profileForm.full_name}
                          onChange={handleProfileChange}
                          error={!!errors.full_name}
                          helperText={errors.full_name}
                          disabled={loading.profile}
                        />
                      </Grid>
                      <Grid item xs={12}>
                        <TextField
                          fullWidth
                          label="Email Address"
                          name="email"
                          type="email"
                          value={profileForm.email}
                          onChange={handleProfileChange}
                          error={!!errors.email}
                          helperText={errors.email}
                          disabled={loading.profile}
                        />
                      </Grid>
                      <Grid item xs={12}>
                        <Button
                          type="submit"
                          variant="contained"
                          disabled={loading.profile}
                          startIcon={loading.profile ? <CircularProgress size={20} /> : null}
                        >
                          {loading.profile ? 'Saving...' : 'Save Changes'}
                        </Button>
                      </Grid>
                    </Grid>
                  </Box>
                </CardContent>
              </Card>
            </Grid>
          </Grid>
        </TabPanel>
        
        <TabPanel value={tabValue} index={1}>
          <Card>
            <CardHeader title="Change Password" />
            <Divider />
            <CardContent>
              <Box component="form" onSubmit={handlePasswordSubmit}>
                <Grid container spacing={3}>
                  <Grid item xs={12}>
                    <TextField
                      fullWidth
                      label="Current Password"
                      name="currentPassword"
                      type="password"
                      value={passwordForm.currentPassword}
                      onChange={handlePasswordChange}
                      error={!!errors.currentPassword}
                      helperText={errors.currentPassword}
                      disabled={loading.password}
                    />
                  </Grid>
                  <Grid item xs={12}>
                    <TextField
                      fullWidth
                      label="New Password"
                      name="newPassword"
                      type="password"
                      value={passwordForm.newPassword}
                      onChange={handlePasswordChange}
                      error={!!errors.newPassword}
                      helperText={errors.newPassword || 'At least 8 characters'}
                      disabled={loading.password}
                    />
                  </Grid>
                  <Grid item xs={12}>
                    <TextField
                      fullWidth
                      label="Confirm New Password"
                      name="confirmPassword"
                      type="password"
                      value={passwordForm.confirmPassword}
                      onChange={handlePasswordChange}
                      error={!!errors.confirmPassword}
                      helperText={errors.confirmPassword}
                      disabled={loading.password}
                    />
                  </Grid>
                  <Grid item xs={12}>
                    <Button
                      type="submit"
                      variant="contained"
                      disabled={loading.password}
                      startIcon={loading.password ? <CircularProgress size={20} /> : null}
                    >
                      {loading.password ? 'Updating...' : 'Update Password'}
                    </Button>
                  </Grid>
                </Grid>
              </Box>
            </CardContent>
          </Card>
        </TabPanel>
        
        <TabPanel value={tabValue} index={2}>
          <Card>
            <CardHeader title="Preferences" />
            <Divider />
            <CardContent>
              <Box component="form" onSubmit={handlePreferencesSubmit}>
                <FormGroup sx={{ mb: 3 }}>
                  <FormControlLabel
                    control={
                      <Switch
                        checked={preferences.darkMode}
                        onChange={handlePreferenceChange}
                        name="darkMode"
                        color="primary"
                      />
                    }
                    label="Dark Mode"
                  />
                  <FormHelperText>
                    Toggle between light and dark theme
                  </FormHelperText>
                </FormGroup>
                
                <FormGroup sx={{ mb: 3 }}>
                  <FormControlLabel
                    control={
                      <Switch
                        checked={preferences.notifications}
                        onChange={handlePreferenceChange}
                        name="notifications"
                        color="primary"
                      />
                    }
                    label="Email Notifications"
                  />
                  <FormHelperText>
                    Receive email notifications for important updates
                  </FormHelperText>
                </FormGroup>
                
                <FormControl fullWidth sx={{ mb: 3 }}>
                  <InputLabel id="language-select-label">Language</InputLabel>
                  <Select
                    labelId="language-select-label"
                    id="language-select"
                    value={preferences.language}
                    label="Language"
                    name="language"
                    onChange={handlePreferenceChange}
                  >
                    <MenuItem value="en">English</MenuItem>
                    <MenuItem value="es">Español</MenuItem>
                    <MenuItem value="fr">Français</MenuItem>
                    <MenuItem value="de">Deutsch</MenuItem>
                  </Select>
                  <FormHelperText>Select your preferred language</FormHelperText>
                </FormControl>
                
                <Button
                  type="submit"
                  variant="contained"
                  disabled={loading.preferences}
                  startIcon={loading.preferences ? <CircularProgress size={20} /> : null}
                >
                  {loading.preferences ? 'Saving...' : 'Save Preferences'}
                </Button>
              </Box>
            </CardContent>
          </Card>
        </TabPanel>
        
        <TabPanel value={tabValue} index={3}>
          <Card>
            <CardHeader 
              title="Danger Zone" 
              titleTypographyProps={{ color: 'error' }}
            />
            <Divider />
            <CardContent>
              <Box sx={{ mb: 4 }}>
                <Typography variant="h6" color="error" gutterBottom>
                  Delete Account
                </Typography>
                <Typography variant="body2" paragraph>
                  Once you delete your account, there is no going back. Please be certain.
                </Typography>
                <Button
                  variant="outlined"
                  color="error"
                  startIcon={<DeleteIcon />}
                  onClick={handleDeleteAccount}
                >
                  Delete My Account
                </Button>
              </Box>
              
              <Divider sx={{ my: 3 }} />
              
              <Box>
                <Typography variant="h6" color="error" gutterBottom>
                  Export Data
                </Typography>
                <Typography variant="body2" paragraph>
                  Download all your data in a JSON format.
                </Typography>
                <Button
                  variant="outlined"
                  color="primary"
                  onClick={() => {
                    // In a real app, this would trigger a data export
                    enqueueSnackbar('Data export is not implemented in this demo', { variant: 'info' });
                  }}
                >
                  Export My Data
                </Button>
              </Box>
            </CardContent>
          </Card>
        </TabPanel>
      </Box>
    </Container>
  );
}

export default SettingsPage;
