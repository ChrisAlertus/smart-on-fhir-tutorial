(function (window) {
  // Configuration - Backend API URL (should be HTTPS)
  // Check window.BACKEND_API_URL first (set in index.html), then fall back to default
  //var BACKEND_API_URL = (typeof window !== 'undefined' && window.BACKEND_API_URL)
  //  ? window.BACKEND_API_URL
  //  : 'https://localhost:8443';
  var BACKEND_API_URL = 'https://wattless-rotundly-celena.ngrok-free.dev';
  console.log('Backend API URL:', BACKEND_API_URL);

  /**
   * Get access token from sessionStorage (managed by fhir-client.js)
   * @returns {string|null} Access token or null if not available
   */
  function getTokenFromSessionStorage() {
    try {
      if (sessionStorage.tokenResponse) {
        var tokenResponse = JSON.parse(sessionStorage.tokenResponse);
        return tokenResponse.access_token || null;
      }
    } catch (e) {
      console.warn('Error reading token from sessionStorage:', e);
    }
    return null;
  }


  /**
   * Make API call to Flask backend
   * Token is extracted from sessionStorage (managed by fhir-client.js)
   * @param {string} endpoint - API endpoint (e.g., '/api/fhir/Patient/123')
   * @param {object} queryParams - Optional query parameters
   * @param {string} fhirServerUrl - Optional FHIR server URL (overrides backend default)
   * @returns {Promise} jQuery deferred promise
   */
  function callBackendAPI(endpoint, queryParams, fhirServerUrl) {
    var ret = $.Deferred();

    // Get token from sessionStorage (managed by fhir-client.js)
    var token = getTokenFromSessionStorage();
    if (!token || !token.trim()) {
      ret.reject('Missing access token in sessionStorage');
      return ret.promise();
    }

    // Build URL
    var backendUrl = (typeof window !== 'undefined' && window.BACKEND_API_URL)
      ? window.BACKEND_API_URL
      : BACKEND_API_URL;
    var url = backendUrl + endpoint;

    // Prepare headers
    var headers = {
      'Authorization': 'Bearer ' + token.trim(),
      'Accept': 'application/json',
      'ngrok-skip-browser-warning': 'true'
    };

    // Add FHIR server URL to headers if provided
    if (fhirServerUrl) {
      headers['X-FHIR-Server-URL'] = fhirServerUrl;
    }

    // Make request with token from sessionStorage
    console.log('Making request to:', url);
    console.log('Token:', token.trim());
    console.log('Query params:', queryParams);
    console.log('FHIR Server URL:', fhirServerUrl || 'using backend default');
    $.ajax({
      url: url,
      method: 'GET',
      headers: headers,
      data: queryParams,
      xhrFields: {
        withCredentials: false
      },
      crossDomain: true
    }).done(function (data) {
      ret.resolve(data);
    }).fail(function (xhr, status, error) {
      console.error('Backend API call failed:', status, error, xhr.responseText);
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
      // Validate smart object
      if (!smart || !smart.hasOwnProperty('patient') || !smart.tokenResponse) {
        console.error('Invalid smart object');
        onError();
        return;
      }

      // Validate access token exists
      if (!smart.tokenResponse.access_token || !smart.tokenResponse.access_token.trim()) {
        console.error('Token response does not have a valid access_token');
        onError();
        return;
      }

      // Token is now stored in sessionStorage.tokenResponse by fhir-client.js
      // We can use it directly from there for backend calls
      const fhirServerUrl = client.state.serverUrl;
      console.log("FHIR Server URL:", fhirServerUrl);
      // Store it for later use if needed
      window.fhirServerUrl = fhirServerUrl;


      // Get patient ID
      var patientId = smart.patient.id;
      if (!patientId) {
        console.error('No patient ID available');
        onError();
        return;
      }

      // Get patient data from backend (token extracted from sessionStorage)
      // Pass fhirServerUrl to backend so it uses the correct FHIR server
      var ptPromise = callBackendAPI('/api/fhir/Patient/' + patientId, null, fhirServerUrl);

      // Get observations from backend (token extracted from sessionStorage)
      // Pass fhirServerUrl to backend so it uses the correct FHIR server
      var obvPromise = callBackendAPI('/api/fhir/Observation', {
        patient: patientId,
        code: 'http://loinc.org|8302-2,http://loinc.org|8462-4,http://loinc.org|8480-6,http://loinc.org|2085-9,http://loinc.org|2089-1,http://loinc.org|55284-4',
        _count: 100
      }, fhirServerUrl);

      $.when(ptPromise, obvPromise).fail(function (patientErr, obvErr) {
        console.error('API call failed - Patient error:', patientErr);
        console.error('API call failed - Observations error:', obvErr);
        onError();
      });

      $.when(ptPromise, obvPromise).done(function (patientResponse, obvResponse) {
        // Extract patient data - backend returns the Patient resource directly
        var patient = patientResponse;

        // Extract observations - backend returns Bundle with entry array
        var observations = [];
        if (obvResponse && obvResponse.entry) {
          observations = obvResponse.entry.map(function (entry) {
            return entry.resource || entry;
          });
        } else if (Array.isArray(obvResponse)) {
          observations = obvResponse;
        }

        console.log('Extracted patient:', patient);
        console.log('Extracted observations count:', observations.length);

        var obv = observations;

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
        p.birthdate = patient.birthDate || '';
        p.gender = gender || '';
        p.fname = fname || '';
        p.lname = lname || '';

        var heightValue = getQuantityValueAndUnit(height && height[0] ? height[0] : undefined);
        p.height = heightValue || '';

        if (typeof systolicbp != 'undefined' && systolicbp) {
          p.systolicbp = systolicbp;
        } else {
          p.systolicbp = '';
        }

        if (typeof diastolicbp != 'undefined' && diastolicbp) {
          p.diastolicbp = diastolicbp;
        } else {
          p.diastolicbp = '';
        }

        var hdlValue = getQuantityValueAndUnit(hdl && hdl[0] ? hdl[0] : undefined);
        p.hdl = hdlValue || '';

        var ldlValue = getQuantityValueAndUnit(ldl && ldl[0] ? ldl[0] : undefined);
        p.ldl = ldlValue || '';

        ret.resolve(p);
      });
    }

    // Use fhir-client.js to handle OAuth2 flow and token management
    // This will:
    // 1. Exchange authorization code for access token (if code present in URL)
    // 2. Store token in sessionStorage.tokenResponse
    // 3. Handle token refresh automatically if needed
    // 4. Call onReady with smart object containing token
    FHIR.oauth2.ready(onReady, onError);

    return ret.promise();
  };

  // Expose function to get current token (for debugging or other uses)
  window.getCurrentToken = function () {
    return getTokenFromSessionStorage();
  };

  function defaultPatient() {
    return {
      fname: '',
      lname: '',
      gender: '',
      birthdate: '',
      height: '',
      systolicbp: '',
      diastolicbp: '',
      ldl: '',
      hdl: '',
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

})(window);
