"use client";

import { FormEvent, useState } from "react";
import { motion } from "framer-motion";
import { EXTERNAL_LINK_PROPS, SOCIAL_LINKS } from "@/components/site";
import {
  FaEnvelope,
  FaClock,
  FaPaperPlane,
} from "react-icons/fa";

const SUPPORT_EMAIL = "support@careerlens.ai";

const subjects = ["Support", "Sales", "Partnership", "Feedback"];

export default function ContactPage() {
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [subject, setSubject] = useState(subjects[0]);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");

  // There is no contact endpoint on the API, so rather than showing a button
  // that silently does nothing, hand the composed message to the user's mail
  // client. This actually delivers.
  const handleSubmit = (e: FormEvent) => {
    e.preventDefault();
    if (!name.trim() || !email.trim() || !message.trim()) {
      setError("Please fill in your name, email, and message.");
      return;
    }
    setError("");
    const body = `${message}\n\n--\n${name}\n${email}`;
    window.location.href = `mailto:${SUPPORT_EMAIL}?subject=${encodeURIComponent(
      `[${subject}] Message from ${name}`
    )}&body=${encodeURIComponent(body)}`;
  };

  return (
    <div className="min-h-screen">
      <section className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-16 lg:py-24">
        <motion.div
          className="text-center max-w-3xl mx-auto"
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6 }}
        >
          <span className="text-sm font-medium text-blue-400 uppercase tracking-wider">
            Contact
          </span>
          <h1 className="text-4xl sm:text-5xl font-bold mt-4 mb-6 leading-tight">
            Get in <span className="gradient-text">touch</span>
          </h1>
          <p className="text-neutral-400 text-lg leading-relaxed">
            Questions about matching, billing, or partnerships. We read
            everything that comes in.
          </p>
        </motion.div>
      </section>

      <section className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 pb-20 lg:pb-32">
        <div className="grid lg:grid-cols-5 gap-6">
          <motion.div
            className="lg:col-span-3 p-6 sm:p-8 rounded-lg bg-neutral-800/50 border border-neutral-700/50"
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.5 }}
          >
            <h2 className="text-xl font-semibold text-neutral-50 mb-6">
              Send us a message
            </h2>

            <form onSubmit={handleSubmit} className="space-y-4">
              <div className="grid sm:grid-cols-2 gap-4">
                <div>
                  <label
                    htmlFor="name"
                    className="block text-sm font-medium text-neutral-300 mb-2"
                  >
                    Your name
                  </label>
                  <input
                    id="name"
                    type="text"
                    value={name}
                    onChange={(e) => setName(e.target.value)}
                    placeholder="Ada Lovelace"
                    className="input-premium"
                  />
                </div>
                <div>
                  <label
                    htmlFor="email"
                    className="block text-sm font-medium text-neutral-300 mb-2"
                  >
                    Your email
                  </label>
                  <input
                    id="email"
                    type="email"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    placeholder="you@example.com"
                    className="input-premium"
                  />
                </div>
              </div>

              <div>
                <label
                  htmlFor="subject"
                  className="block text-sm font-medium text-neutral-300 mb-2"
                >
                  Subject
                </label>
                <select
                  id="subject"
                  value={subject}
                  onChange={(e) => setSubject(e.target.value)}
                  className="input-premium"
                >
                  {subjects.map((s) => (
                    <option key={s} value={s} className="bg-neutral-800">
                      {s}
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label
                  htmlFor="message"
                  className="block text-sm font-medium text-neutral-300 mb-2"
                >
                  Message
                </label>
                <textarea
                  id="message"
                  rows={6}
                  value={message}
                  onChange={(e) => setMessage(e.target.value)}
                  placeholder="Tell us what you need help with..."
                  className="input-premium resize-y"
                />
              </div>

              {error && (
                <p className="text-sm text-rose-300 bg-rose-500/10 border border-rose-500/30 rounded-lg px-4 py-3">
                  {error}
                </p>
              )}

              <button
                type="submit"
                className="btn-primary inline-flex items-center gap-2"
              >
                <FaPaperPlane className="w-4 h-4" />
                Send message
              </button>

              <p className="text-xs text-neutral-500">
                This opens your email client with the message ready to send.
              </p>
            </form>
          </motion.div>

          <motion.div
            className="lg:col-span-2 space-y-4"
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.5, delay: 0.1 }}
          >
            <div className="p-6 rounded-lg bg-neutral-800/50 border border-neutral-700/50">
              <div className="w-11 h-11 rounded-lg bg-gradient-to-br from-blue-500 to-blue-600 flex items-center justify-center mb-4 shadow-lg">
                <FaEnvelope className="w-4 h-4 text-white" />
              </div>
              <h3 className="text-sm font-semibold text-neutral-200 uppercase tracking-wider mb-2">
                Email
              </h3>
              <a
                href={`mailto:${SUPPORT_EMAIL}`}
                className="text-blue-400 hover:text-blue-300 transition-colors"
              >
                {SUPPORT_EMAIL}
              </a>
            </div>

            <div className="p-6 rounded-lg bg-neutral-800/50 border border-neutral-700/50">
              <div className="w-11 h-11 rounded-lg bg-gradient-to-br from-emerald-500 to-emerald-600 flex items-center justify-center mb-4 shadow-lg">
                <FaClock className="w-4 h-4 text-white" />
              </div>
              <h3 className="text-sm font-semibold text-neutral-200 uppercase tracking-wider mb-2">
                Response time
              </h3>
              <p className="text-neutral-400 text-sm">
                Typically within 24 hours on weekdays.
              </p>
            </div>

            <div className="p-6 rounded-lg bg-neutral-800/50 border border-neutral-700/50">
              <h3 className="text-sm font-semibold text-neutral-200 uppercase tracking-wider mb-4">
                Social
              </h3>
              <div className="flex items-center gap-3">
                {SOCIAL_LINKS.map((s) => (
                  <a
                    key={s.label}
                    href={s.href}
                    aria-label={s.label}
                    {...EXTERNAL_LINK_PROPS}
                    className="w-10 h-10 rounded-lg bg-neutral-800 border border-neutral-700/50 flex items-center justify-center text-neutral-400 hover:text-neutral-50 hover:border-neutral-600 transition-all duration-200"
                  >
                    <s.icon className="w-4 h-4" />
                  </a>
                ))}
              </div>
            </div>
          </motion.div>
        </div>
      </section>
    </div>
  );
}
