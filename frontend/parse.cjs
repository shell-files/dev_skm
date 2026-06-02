const http = require('http');

http.get('http://skm.weareithero.cloud', res => {
  let data = '';
  res.on('data', chunk => { data += chunk; });
  res.on('end', () => {
    const match = data.match(/\/assets\/index-[^"]+\.js/);
    console.log('NEW Bundle Hash:', match ? match[0] : 'not found');
  });
});
