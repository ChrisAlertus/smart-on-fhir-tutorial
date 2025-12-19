(function (window) {
  // Configuration - Backend API URL (should be HTTPS)
  // Check window.BACKEND_API_URL first (set in index.html), then fall back to default
  //var BACKEND_API_URL = (typeof window !== 'undefined' && window.BACKEND_API_URL)
  //  ? window.BACKEND_API_URL
  //  : 'https://localhost:8443';
  var BACKEND_API_URL = 'https://wattless-rotundly-celena.ngrok-free.dev';
  console.log('Backend API URL:', BACKEND_API_URL);

  // Cookie management functions
  function setCookie(name, value, days) {
    var expires = "";
    if (days) {
      var date = new Date();
      date.setTime(date.getTime() + (days * 24 * 60 * 60 * 1000));
      expires = "; expires=" + date.toUTCString();
    }
    // Secure flag for HTTPS, SameSite for CSRF protection
    var secureFlag = window.location.protocol === 'https:' ? '; Secure' : '';
    document.cookie = name + "=" + (value || "") + expires + "; path=/" + secureFlag + "; SameSite=Strict";
  }

  function getCookie(name) {
    var nameEQ = name + "=";
    var ca = document.cookie.split(';');
    for (var i = 0; i < ca.length; i++) {
      var c = ca[i];
      while (c.charAt(0) === ' ') c = c.substring(1, c.length);
      if (c.indexOf(nameEQ) === 0) return c.substring(nameEQ.length, c.length);
    }
    return null;
  }

  function deleteCookie(name) {
    document.cookie = name + "=; expires=Thu, 01 Jan 1970 00:00:00 UTC; path=/;";
  }

  // Token management functions
  function setTokenCookie(tokenResponse) {
    if (tokenResponse && tokenResponse.access_token) {
      // Store access token
      setCookie('fhir_access_token', tokenResponse.access_token, 1); // 1 day default

      // Store refresh token if available
      if (tokenResponse.refresh_token) {
        setCookie('fhir_refresh_token', tokenResponse.refresh_token, 30); // 30 days
      }

      // Store token expiration
      if (tokenResponse.expires_in) {
        var expiresAt = new Date().getTime() + (tokenResponse.expires_in * 1000);
        setCookie('fhir_token_expires_at', expiresAt.toString(), 1);
      }

      // Store patient ID if available
      if (tokenResponse.patient) {
        setCookie('fhir_patient_id', tokenResponse.patient, 1);
      }

      // Store full token response for reference
      setCookie('fhir_token_response', JSON.stringify(tokenResponse), 1);
    }
  }

  function getTokenCookie() {
    return getCookie('fhir_access_token');
  }

  function getRefreshTokenCookie() {
    return getCookie('fhir_refresh_token');
  }

  function getPatientIdCookie() {
    return getCookie('fhir_patient_id');
  }

  function clearTokenCookie() {
    deleteCookie('fhir_access_token');
    deleteCookie('fhir_refresh_token');
    deleteCookie('fhir_token_expires_at');
    deleteCookie('fhir_patient_id');
    deleteCookie('fhir_token_response');
  }

  function isTokenExpired() {
    var expiresAt = getCookie('fhir_token_expires_at');
    if (!expiresAt) return true;

    var expirationTime = parseInt(expiresAt, 10);
    var currentTime = new Date().getTime();

    // Check if token expires within the next 5 minutes
    return currentTime >= (expirationTime - 5 * 60 * 1000);
  }

  // Token refresh function
  function refreshToken(smart) {
    var ret = $.Deferred();
    var refreshToken = getRefreshTokenCookie();

    if (!refreshToken) {
      ret.reject('No refresh token available');
      return ret.promise();
    }

    // Use fhir-client to refresh the token
    if (smart && smart.tokenResponse) {
      smart.tokenResponse.refresh_token = refreshToken;

      // Call the refresh function from fhir-client
      if (typeof FHIR !== 'undefined' && FHIR.oauth2 && FHIR.oauth2.refresh) {
        FHIR.oauth2.refresh(smart).done(function (newTokenResponse) {
          setTokenCookie(newTokenResponse);
          ret.resolve(newTokenResponse);
        }).fail(function (error) {
          console.error('Token refresh failed:', error);
          clearTokenCookie();
          ret.reject(error);
        });
      } else {
        // Fallback: manually refresh using the token endpoint
        var state = JSON.parse(sessionStorage[smart.tokenResponse.state] || '{}');
        if (state && state.provider && state.provider.oauth2 && state.provider.oauth2.token_uri) {
          $.ajax({
            url: state.provider.oauth2.token_uri,
            method: 'POST',
            data: {
              grant_type: 'refresh_token',
              refresh_token: refreshToken
            }
          }).done(function (newTokenResponse) {
            setTokenCookie(newTokenResponse);
            ret.resolve(newTokenResponse);
          }).fail(function (error) {
            console.error('Token refresh failed:', error);
            clearTokenCookie();
            ret.reject(error);
          });
        } else {
          ret.reject('Unable to refresh token: token endpoint not found');
        }
      }
    } else {
      ret.reject('Smart object not available for token refresh');
    }

    return ret.promise();
  }

  // Token revocation function
  function revokeToken(smart) {
    var ret = $.Deferred();
    var accessToken = getTokenCookie();

    if (!accessToken) {
      ret.resolve('No token to revoke');
      return ret.promise();
    }

    // Get revocation endpoint from smart object or state
    var revocationUrl = null;
    if (smart && smart.tokenResponse) {
      var state = JSON.parse(sessionStorage[smart.tokenResponse.state] || '{}');
      if (state && state.provider && state.provider.oauth2 && state.provider.oauth2.revocation_uri) {
        revocationUrl = state.provider.oauth2.revocation_uri;
      }
    }

    if (!revocationUrl) {
      // Try to get from metadata
      var tokenResponse = getCookie('fhir_token_response');
      if (tokenResponse) {
        try {
          var tokenData = JSON.parse(tokenResponse);
          if (tokenData.state) {
            var state = JSON.parse(sessionStorage[tokenData.state] || '{}');
            if (state && state.provider && state.provider.oauth2 && state.provider.oauth2.revocation_uri) {
              revocationUrl = state.provider.oauth2.revocation_uri;
            }
          }
        } catch (e) {
          console.error('Error parsing token response:', e);
        }
      }
    }

    if (revocationUrl) {
      $.ajax({
        url: revocationUrl,
        method: 'POST',
        data: {
          token: accessToken,
          token_type_hint: 'access_token'
        }
      }).done(function () {
        clearTokenCookie();
        ret.resolve('Token revoked successfully');
      }).fail(function (error) {
        console.error('Token revocation failed:', error);
        // Clear cookies anyway
        clearTokenCookie();
        ret.reject(error);
      });
    } else {
      // If no revocation endpoint, just clear cookies
      clearTokenCookie();
      ret.resolve('Token cleared (no revocation endpoint available)');
    }

    return ret.promise();
  }

  // Make API call to Flask backend
  function callBackendAPI(endpoint, token, queryParams) {
    var ret = $.Deferred();
    // Use window.BACKEND_API_URL if set, otherwise fall back to BACKEND_API_URL variable
    var backendUrl = (typeof window !== 'undefined' && window.BACKEND_API_URL)
      ? window.BACKEND_API_URL
      : BACKEND_API_URL;
    var url = backendUrl + endpoint;

    console.log('Making API call to:', url);
    console.log('Backend URL source:', (typeof window !== 'undefined' && window.BACKEND_API_URL) ? 'window.BACKEND_API_URL' : 'BACKEND_API_URL variable');

    var headers = {
      'Authorization': 'Bearer ' + token,
      'Accept': 'application/json',
      'Content-Type': 'application/json'
    };

    $.ajax({
      url: url,
      method: 'GET',
      headers: headers,
      data: queryParams,
      // Note: withCredentials requires exact CORS origin, not "*"
      xhrFields: {
        withCredentials: false  // Set to false since we're using Authorization header
      }
    }).done(function (data) {
      ret.resolve(data);
    }).fail(function (xhr, status, error) {
      console.error('Backend API call failed:', status, error);
      ret.reject(xhr, status, error);
    });

    return ret.promise();
  }

  window.extractData = function () {
    var ret = $.Deferred();

    function onError() {
      console.log('Loading error', arguments);
      ret.reject();
    }

    function onReady(smart) {
      // Validate smart object and token response
      if (!smart) {
        console.error('Smart object is null or undefined');
        onError();
        return;
      }

      if (!smart.hasOwnProperty('patient')) {
        console.error('Smart object does not have patient property');
        onError();
        return;
      }

      if (!smart.tokenResponse) {
        console.error('Smart object does not have tokenResponse');
        onError();
        return;
      }

      // Validate access token exists and is not empty
      if (!smart.tokenResponse.access_token || smart.tokenResponse.access_token.trim() === '') {
        console.error('Token response does not have a valid access_token');
        onError();
        return;
      }

      // Store token in cookie
      setTokenCookie(smart.tokenResponse);

      // Get patient ID
      var patientId = smart.patient.id || getPatientIdCookie();

      if (!patientId) {
        console.error('No patient ID available');
        onError();
        return;
      }

      // Check if token needs refresh
      var tokenPromise = $.Deferred().resolve(smart.tokenResponse);
      if (isTokenExpired()) {
        console.log('Token expired, attempting refresh...');
        tokenPromise = refreshToken(smart);
      }

      tokenPromise.done(function (tokenResponse) {
        var accessToken = tokenResponse.access_token || getTokenCookie();

        if (!accessToken) {
          onError();
          return;
        }

        // Get patient data from backend
        var ptPromise = callBackendAPI('/api/fhir/Patient/' + patientId, accessToken);

        // Get observations from backend
        // Note: FHIR code parameter format may vary by server
        // Using multiple code parameters or comma-separated values
        var obvPromise = callBackendAPI('/api/fhir/Observation', accessToken, {
          patient: patientId,
          code: 'http://loinc.org|8302-2,http://loinc.org|8462-4,http://loinc.org|8480-6,http://loinc.org|2085-9,http://loinc.org|2089-1,http://loinc.org|55284-4',
          _count: 100
        });

        $.when(ptPromise, obvPromise).fail(onError);

        $.when(ptPromise, obvPromise).done(function (patientResponse, obvResponse) {
          // Extract patient data
          var patient = patientResponse;
          var observations = obvResponse.entry || [];
          var obv = observations.map(function (entry) { return entry.resource; });

          // Use smart.byCodes if available, otherwise create a simple lookup
          var byCodes = smart.byCodes || function (observations, codeField) {
            return function (code) {
              return observations.filter(function (obs) {
                if (!obs.code || !obs.code.coding) return false;
                return obs.code.coding.some(function (coding) {
                  return coding.code === code ||
                    (coding.system && coding.code &&
                      (coding.system + '|' + coding.code).endsWith('|' + code));
                });
              });
            };
          };

          var byCodesFunc = byCodes(obv, 'code');
          var gender = patient.gender;

          var fname = '';
          var lname = '';

          if (typeof patient.name !== 'undefined' && patient.name.length > 0) {
            lname = Array.isArray(patient.name[0].family)
              ? patient.name[0].family.join(" ")
              : (patient.name[0].family || "");
            fname = Array.isArray(patient.name[0].given)
              ? patient.name[0].given.join(" ")
              : (patient.name[0].given || "");
          }

          var height = byCodesFunc('8302-2');
          var systolicbp = getBloodPressureValue(byCodesFunc('55284-4'), '8480-6');
          var diastolicbp = getBloodPressureValue(byCodesFunc('55284-4'), '8462-4');
          var hdl = byCodesFunc('2085-9');
          var ldl = byCodesFunc('2089-1');

          var p = defaultPatient();
          p.birthdate = patient.birthDate;
          p.gender = gender;
          p.fname = fname;
          p.lname = lname;

          p.height = getQuantityValueAndUnit(height[0]);

          if (typeof systolicbp != 'undefined') {
            p.systolicbp = systolicbp;
          }

          if (typeof diastolicbp != 'undefined') {
            p.diastolicbp = diastolicbp;
          }

          p.hdl = getQuantityValueAndUnit(hdl[0]);
          p.ldl = getQuantityValueAndUnit(ldl[0]);

          ret.resolve(p);
        });
      }).fail(function (error) {
        console.error('Token refresh failed:', error);
        onError();
      });
    } else {
      onError();
    }
  }

  // Check if we have a stored token
  var storedToken = getTokenCookie();
  if (storedToken && !isTokenExpired()) {
    // Use stored token, but we still need the smart object for patient context
    // So we'll still call FHIR.oauth2.ready but it should use the stored token
    FHIR.oauth2.ready(onReady, onError);
  } else {
    console.error('No OAuth callback detected and no token in storage. Redirect to launch page.');
    onError();
  }
} catch (error) {
  console.error('Error calling FHIR.oauth2.ready:', error);
  // If it's the specific JWT decode error, try to continue anyway
  if (error.message && error.message.includes('exp')) {
    console.warn('JWT decode error detected, but attempting to continue...');
    // Try to get token from sessionStorage directly
    try {
      if (sessionStorage.tokenResponse) {
        var storedToken = JSON.parse(sessionStorage.tokenResponse);
        if (storedToken && storedToken.access_token) {
          // Create a minimal smart object
          var minimalSmart = {
            tokenResponse: storedToken,
            patient: { id: getPatientIdCookie() }
          };
          onReady(minimalSmart);
          return ret.promise();
        }
      }
    } catch (e) {
      console.error('Failed to recover from error:', e);
    }
  }
  onError();
}

return ret.promise();

  };

// Expose token management functions
window.revokeToken = function () {
  // Get smart object from sessionStorage if available
  var tokenResponse = getCookie('fhir_token_response');
  var smart = null;
  if (tokenResponse) {
    try {
      var tokenData = JSON.parse(tokenResponse);
      if (tokenData.state) {
        var state = JSON.parse(sessionStorage[tokenData.state] || '{}');
        if (state) {
          smart = { tokenResponse: tokenData };
        }
      }
    } catch (e) {
      console.error('Error parsing token response:', e);
    }
  }
  return revokeToken(smart);
};

function defaultPatient() {
  return {
    fname: { value: '' },
    lname: { value: '' },
    gender: { value: '' },
    birthdate: { value: '' },
    height: { value: '' },
    systolicbp: { value: '' },
    diastolicbp: { value: '' },
    ldl: { value: '' },
    hdl: { value: '' },
  };
}

function getBloodPressureValue(BPObservations, typeOfPressure) {
  var formattedBPObservations = [];
  BPObservations.forEach(function (observation) {
    var BP = observation.component.find(function (component) {
      return component.code.coding.find(function (coding) {
        return coding.code == typeOfPressure;
      });
    });
    if (BP) {
      observation.valueQuantity = BP.valueQuantity;
      formattedBPObservations.push(observation);
    }
  });

  return getQuantityValueAndUnit(formattedBPObservations[0]);
}

function getQuantityValueAndUnit(ob) {
  if (typeof ob != 'undefined' &&
    typeof ob.valueQuantity != 'undefined' &&
    typeof ob.valueQuantity.value != 'undefined' &&
    typeof ob.valueQuantity.unit != 'undefined') {
    return ob.valueQuantity.value + ' ' + ob.valueQuantity.unit;
  } else {
    return undefined;
  }
}

window.drawVisualization = function (p) {
  $('#holder').show();
  $('#loading').hide();
  $('#fname').html(p.fname);
  $('#lname').html(p.lname);
  $('#gender').html(p.gender);
  $('#birthdate').html(p.birthdate);
  $('#height').html(p.height);
  $('#systolicbp').html(p.systolicbp);
  $('#diastolicbp').html(p.diastolicbp);
  $('#ldl').html(p.ldl);
  $('#hdl').html(p.hdl);
};

}) (window);
