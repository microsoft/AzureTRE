define([], function () {
  var configLocal = {};

  // clearing local storage otherwise source cache will obscure the override settings
  localStorage.clear();

  var getUrl = window.location;
  var baseUrl = getUrl.protocol + "//" + getUrl.host;

  // WebAPI
  configLocal.api = {
    name: 'OHDSI',
    url: baseUrl + '/WebAPI/'
  };

  configLocal.cohortComparisonResultsEnabled = false;
  configLocal.userAuthenticationEnabled = false;
  configLocal.plpResultsEnabled = false;

  return configLocal;
});
