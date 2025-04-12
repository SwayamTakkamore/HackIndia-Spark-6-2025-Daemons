import 'dart:convert';
import 'package:http/http.dart' as http;

class ApiService {
  static const String _baseUrl = 'http://192.168.54.199:8000';

  static Future<http.Response> uploadFile(String filePath) async {
    var request = http.MultipartRequest('POST', Uri.parse('$_baseUrl/upload'));
    request.files.add(await http.MultipartFile.fromPath('file', filePath));
    return await http.Response.fromStream(await request.send());
  }

  static Future<http.Response> queryDocument(String prompt) async {
    return await http.post(
      Uri.parse('$_baseUrl/query'),
      body: {'prompt': prompt},
      headers: {'Content-Type': 'application/x-www-form-urlencoded'},
    );
  }
}